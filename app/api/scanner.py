"""Handles Barcode lookups and Vision-based metadata extraction."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
import copy
import hashlib
import io
import re

from flask import current_app, g, jsonify, request
from PIL import Image
from sqlalchemy import or_

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import require_auth, require_permission
from app.core.ingest import IngestService
from app.core.permissions import PermissionName
from app.core.tasks import get_task_result, submit_task
from app.db.models import Expression, Item, Manifestation, ScanTelemetry, db
from app.strategies.lookup import LookupStrategyFactory
from app.utils.discogs import fetch_discogs_candidates, fetch_discogs_by_id
from app.utils.vision import extract_metadata_from_cover

# Maximum allowed upload size for cover images (10 MB)
_MAX_COVER_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _read_bounded(file_storage, max_bytes: int) -> bytes | None:
    """Read at most *max_bytes* from *file_storage*.

    Reads exactly ``max_bytes + 1`` bytes in a single call so that the result
        fits in one allocation and we can detect an oversized payload without
        buffering the whole stream first.

    Returns:
        The raw bytes when the payload is within the limit, or ``None`` when it
        exceeds *max_bytes*.
    """
    buf = file_storage.read(max_bytes + 1)
    return None if len(buf) > max_bytes else buf


def _record_scan_telemetry(
    barcode: str,
    format_hint: str | None,
    provider: str,
    status: str,
    manifestation_id: int | None = None,
    raw_request_url: str | None = None,
) -> None:
    """Helper to persist a scan-lookup record safely."""
    try:
        # Create a savepoint to prevent rollback of outer transactions
        with db.session.begin_nested():
            telemetry = ScanTelemetry(
                barcode=barcode,
                format_hint=format_hint,
                provider=provider,
                status=status,
                manifestation_id=manifestation_id,
                raw_request_url=raw_request_url,
            )
            db.session.add(telemetry)
        db.session.commit()
    except Exception:  # pylint: disable=broad-except
        # The savepoint is automatically rolled back, main transaction is safe
        current_app.logger.exception("Failed to record scan telemetry")


def _get_manifestation_filters(code: str):
    """Unified filters to find manifestation by ANY identifier."""
    return [
        Manifestation.isbn13 == code,
        Manifestation.upc == code,
        Manifestation.ean == code,
        Manifestation.meta["isbn"].as_string() == code,
        Manifestation.meta["barcode"].as_string() == code,
        Manifestation.meta["discogs_id"].as_string() == code,
        Manifestation.meta["hash_id"].as_string() == code,
    ]


def _find_locally(code: str) -> Manifestation | None:
    """Unified helper to find manifestation by identifier."""
    # pylint: disable=singleton-comparison
    result = Manifestation.query.filter(or_(*_get_manifestation_filters(code))).first()
    return result if isinstance(result, Manifestation) else None


def _ingest_by_hint(barcode: str, category_hint: str | None, format_hint: str | None) -> Manifestation:
    """Waterfall helper to ingest based on format hint. Drastically reduces cyclomatic complexity."""
    if category_hint == "music":
        return IngestService.ingest_audio_from_barcode(barcode)
    if category_hint == "movie":
        return IngestService.ingest_video_from_barcode(barcode)
    if category_hint == "board_game":
        return IngestService.ingest_game_from_barcode(barcode)
    if category_hint == "puzzle":
        return IngestService.ingest_puzzle_from_barcode(barcode)
    if category_hint == "text" or format_hint == "audiobook":
        return IngestService.ingest_from_isbn(barcode)

    # Auto-fallback strategy
    is_isbn_like = len(barcode) == 13 and (barcode.startswith("978") or barcode.startswith("979")) or len(barcode) == 10
    if is_isbn_like:
        try:
            return IngestService.ingest_from_isbn(barcode)
        except ValueError:
            return IngestService.ingest_audio_from_barcode(barcode)

    # Waterfall trial for unknown pure barcode formats
    for ingest_func in [
        IngestService.ingest_audio_from_barcode,
        IngestService.ingest_video_from_barcode,
        IngestService.ingest_game_from_barcode,
        IngestService.ingest_puzzle_from_barcode,
        IngestService.ingest_from_isbn
    ]:
        try:
            return ingest_func(barcode)
        except ValueError:
            continue
            
    raise ValueError("Exhausted all ingestion methods")


@api_bp.route("/lookup/<query>", methods=["GET"])
@require_auth
def lookup_barcode_preview(query: str):
    """Generic identifier lookup for preview (barcode, ISBN, or name hash)."""
    format_hint = request.args.get("format")

    # Heuristic: if query has spaces or no digits, treat as name and hash it
    is_barcode = any(char.isdigit() for char in query) and " " not in query
    canonical_id = query

    if not is_barcode:
        # Create deterministic hash for name-lookup
        normalized_name = query.strip().lower()
        canonical_id = hashlib.sha256(normalized_name.encode()).hexdigest()[:16]
        current_app.logger.debug(f"Hashed search '{query}' to {canonical_id}")

    # Check DB first
    query_obj = Manifestation.query.join(Expression).filter(or_(*_get_manifestation_filters(canonical_id)))

    from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY
    category_hint = FORMAT_ALIAS_TO_CATEGORY.get(format_hint) if format_hint else None

    # Filter by format if hint is provided to avoid cross-media collisions
    if category_hint:
        query_obj = query_obj.filter(Expression.content_type == category_hint)

    all_manifestations = query_obj.all()
    manifestation = all_manifestations[0] if all_manifestations else None

    if manifestation and manifestation.meta:
        # Check if we have multiple candidates
        candidates = []
        if len(all_manifestations) > 1:
            user_id = getattr(g, "user_id", None)
            # Fetch all items owned by user for these manifestations in one go
            m_ids = [m.id for m in all_manifestations]
            user_items = Item.query.filter(Item.manifestation_id.in_(m_ids), Item.owner_id == user_id).all()
            owned_ids = {i.manifestation_id: i.id for i in user_items}

            for m in all_manifestations:
                if not m.meta:
                    continue
                cand = dict(m.meta)
                cand["manifestation_id"] = m.id
                cand["already_in_db"] = True
                cand["already_in_collection"] = m.id in owned_ids
                cand["item_id"] = owned_ids.get(m.id)
                candidates.append(cand)

        data = dict(manifestation.meta)
        data["manifestation_id"] = manifestation.id
        data["already_in_db"] = True
        # Show the original human-readable query, not the internal hash
        data["identifier"] = query
        if candidates:
            data["candidates"] = candidates

        # Check if user owns it
        user_id = getattr(g, "user_id", None)
        item = Item.query.filter_by(manifestation_id=manifestation.id, owner_id=user_id).first()
        data["already_in_collection"] = item is not None
        data["item_id"] = item.id if item else None

        _record_scan_telemetry(canonical_id, format_hint, "database", "success", manifestation.id)
        return jsonify({"success": True, "data": data, "error": None}), 200

    barcode = query if not is_barcode else canonical_id

    # For non-barcode text queries on audio/unspecified format, fetch multiple Discogs candidates
    if not is_barcode and (category_hint == "music" or format_hint in (None, "")):
        discogs_results = fetch_discogs_candidates(query)
        if len(discogs_results) > 1:
            response_data = copy.deepcopy(discogs_results[0])
            response_data["candidates"] = discogs_results
            response_data["identifier"] = query
            response_data["already_in_collection"] = False
            response_data["item_id"] = None
            response_data["data_source"] = "discogs"
            for candidate in discogs_results:
                candidate["data_source"] = "discogs"
            _record_scan_telemetry(query, format_hint, "discogs", "success")
            return jsonify({"success": True, "data": response_data, "error": None}), 200

    # Leverage the Strategy Pattern
    strategy = LookupStrategyFactory.get_strategy(category_hint)
    meta, provider = strategy.lookup(barcode, query)

    if not meta:
        _record_scan_telemetry(barcode, format_hint, provider=format_hint or "unknown", status="failed")
        return jsonify({"success": False, "data": None, "error": f"No metadata found for barcode {barcode}"}), 404

    # Ensure frontend gets normalized keys for preview
    if "title" not in meta:
        meta["title"] = meta.get("Title") or "Unknown Title"
    if "cover_url" not in meta:
        cover_val = meta.get("thumb") or meta.get("cover")
        if isinstance(cover_val, dict):
            meta["cover_url"] = cover_val.get("large") or cover_val.get("medium") or cover_val.get("small")
        elif isinstance(cover_val, list) and len(cover_val) > 0:
            meta["cover_url"] = cover_val[0]
        else:
            meta["cover_url"] = cover_val
    if "author" not in meta:
        meta["author"] = (
            meta.get("artist") or meta.get("Artist") or meta.get("manufacturer") or meta.get("brand") or meta.get("authors", [None])[0]
        )

    if "format" not in meta and format_hint:
        from app.core.taxonomy import FORMAT_TO_CATEGORY
        from app.db.core import MediaFormat

        # Use canonical mapping from taxonomy
        meta["format"] = format_hint if format_hint in FORMAT_TO_CATEGORY else format_hint.upper()

        # Map generic hints to default formats
        hint_to_format = {
            "audio": MediaFormat.CD,
            "music": MediaFormat.CD,
            "video": MediaFormat.DVD,
            "movie": MediaFormat.DVD,
            "game": MediaFormat.BOARD_GAME,
            "boardgame": MediaFormat.BOARD_GAME,
            "book": MediaFormat.BOOK,
            "text": MediaFormat.BOOK,
            "puzzle": MediaFormat.JIGSAW_PUZZLE,
            "jigsaw": MediaFormat.JIGSAW_PUZZLE,
            "audiobook": MediaFormat.AUDIOBOOK_CD,
        }
        if format_hint in hint_to_format:
            meta["format"] = hint_to_format[format_hint]

    # Add identifier to meta
    meta["identifier"] = query
    meta["already_in_collection"] = False

    # Auto-save to catalog so the user never has to click an extra button.
    manifestation_id: int | None = None
    try:
        meta_to_store = {k: v for k, v in meta.items() if k not in ("already_in_collection", "item_id", "candidates", "already_in_db")}
        if not is_barcode and canonical_id:
            meta_to_store["hash_id"] = canonical_id
        if is_barcode and canonical_id and "barcode" not in meta_to_store:
            meta_to_store["barcode"] = canonical_id
        saved = IngestService.ingest_from_meta(meta_to_store)
        manifestation_id = saved.id
    except Exception:  # pylint: disable=broad-except
        current_app.logger.debug("Auto-save to catalog skipped (manifestation may already exist or error occurred)")
        # Try finding it in case it already exists
        existing = _find_locally(canonical_id)
        if existing:
            manifestation_id = existing.id

    meta["manifestation_id"] = manifestation_id

    # Check collection ownership with the now-known manifestation_id
    if manifestation_id:
        user_id = getattr(g, "user_id", None)
        item = Item.query.filter_by(manifestation_id=manifestation_id, owner_id=user_id).first()
        meta["already_in_collection"] = item is not None
        meta["item_id"] = item.id if item else None

    # Record successful external lookup
    _record_scan_telemetry(barcode, format_hint, provider=provider or "external", status="success", manifestation_id=manifestation_id)

    return jsonify({"success": True, "data": meta, "error": None}), 200


@api_bp.route("/scan", methods=["POST"])
@require_auth
def scan_barcode():
    """Scan a barcode and add the corresponding item to the authenticated user's collection."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    barcode = data.get("barcode")
    manifestation_id = data.get("manifestation_id")
    format_hint = data.get("format")
    collection_status = data.get("collection_status", "available")  # Defaults to available, accepts wishlist

    if not barcode and not manifestation_id:
        return jsonify({"success": False, "data": None, "error": "Barcode or Manifestation ID is required"}), 400

    is_new_manifestation = False
    manifestation = None

    # Priority 1: Direct Manifestation ID
    if manifestation_id:
        manifestation = db.session.get(Manifestation, manifestation_id)

    # Priority 2: Check DB by barcode
    if not manifestation and barcode:
        manifestation = _find_locally(barcode)

        from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY
        category_hint = FORMAT_ALIAS_TO_CATEGORY.get(format_hint) if format_hint else None

        try:
            # Support pure numeric Discogs Release IDs
            is_discogs_numeric = barcode.isdigit() and len(barcode) <= 8
            if is_discogs_numeric and (category_hint == "music" or format_hint is None):
                meta = fetch_discogs_by_id(barcode)
                if meta:
                    manifestation = IngestService.ingest_from_meta(meta)

            if not manifestation:
                manifestation = _ingest_by_hint(barcode, category_hint, format_hint)
            is_new_manifestation = True
            
        except ValueError as e:
            return jsonify({"success": False, "data": None, "error": f"Invalid barcode or not found: {str(e)}"}), 400
        except ConnectionError as e:
            return jsonify({"success": False, "data": None, "error": f"Network error while fetching metadata: {str(e)}"}), 503
        except Exception as e:  # pylint: disable=broad-except
            _record_scan_telemetry(barcode, format_hint, provider=format_hint or "ingest", status="failed")
            return jsonify({"success": False, "data": None, "error": f"Failed to find or ingest metadata for barcode: {str(e)}"}), 404

    if not manifestation:
        _record_scan_telemetry(barcode, format_hint, provider=format_hint or "ingest", status="failed")
        return jsonify({"success": False, "data": None, "error": "Could not resolve barcode"}), 404

    from app.db.core import CATEGORY_PROGRESS_STATUSES
    content_type = manifestation.expression.content_type if manifestation.expression else "text"
    default_progress = CATEGORY_PROGRESS_STATUSES.get(content_type, ("want_to_read",))[0]

    # Assign dynamically passed collection_status (Library vs Wishlist)
    new_item = Item(
        manifestation_id=manifestation.id, 
        owner_id=getattr(g, "user_id", None), 
        status=default_progress, 
        collection_status=collection_status
    )
    db.session.add(new_item)

    # For name-based lookups (no barcode), store the hash_id in meta
    if barcode:
        is_barcode_like = bool(re.match(r"^[\dX]{8,14}$", barcode.strip().upper()))
        if not is_barcode_like and manifestation.meta and not manifestation.meta.get("hash_id"):
            computed_hash = hashlib.sha256(barcode.strip().lower().encode()).hexdigest()[:16]
            updated_meta = dict(manifestation.meta)
            updated_meta["hash_id"] = computed_hash
            manifestation.meta = updated_meta

    db.session.commit()

    # Success: record telemetry with manifestation_id
    _record_scan_telemetry(
        barcode or manifestation.title, format_hint, provider=format_hint or "ingest", status="success", manifestation_id=manifestation.id
    )

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "message": "Item successfully added to your collection",
                    "identifier_label": "ISBN" if (manifestation.meta.get("isbn") or "").strip() else "Barcode",
                    "identifier_value": manifestation.meta.get("isbn") or manifestation.meta.get("barcode"),
                    "item_id": new_item.id,
                    "manifestation_id": manifestation.id,
                    "title": (
                        manifestation.meta.get("title") or manifestation.meta.get("Title") if manifestation.meta else manifestation.title
                    ),
                    "author": (
                        manifestation.meta.get("author") or (manifestation.meta.get("authors") or [None])[0]
                        if manifestation.meta
                        else manifestation.author
                    ),
                    "cover_url": (
                        manifestation.meta.get("cover_url") or manifestation.meta.get("thumb")
                        if manifestation.meta
                        else manifestation.cover_url
                    ),
                    "is_new_manifestation": is_new_manifestation,
                },
                "error": None,
            }
        ),
        201,
    )


@api_bp.route("/vision/extract", methods=["POST"])
@require_auth
@require_permission(PermissionName.LLM_GENERATE_METADATA)
def extract_from_cover():
    """Submit a cover image for asynchronous metadata extraction."""
    if "cover" not in request.files:
        return jsonify({"success": False, "data": None, "error": "No file provided"}), 400

    file = request.files["cover"]
    if not file.filename:
        return jsonify({"success": False, "data": None, "error": "No selected file"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": f"Invalid file type. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
                }
            ),
            400,
        )

    if request.content_length and request.content_length > _MAX_COVER_SIZE:
        return jsonify({"success": False, "data": None, "error": "File too large. Max size: 10 MB"}), 413

    image_bytes = _read_bounded(file, _MAX_COVER_SIZE)
    if image_bytes is None:
        return jsonify({"success": False, "data": None, "error": "File too large. Max size: 10 MB"}), 413

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except (OSError, SyntaxError):
        return jsonify({"success": False, "data": None, "error": "Invalid or corrupted image file"}), 400

    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")
    user_id = getattr(g, "user_id", None)

    # Dispatch to background task queue
    task_id = submit_task(extract_metadata_from_cover, image_bytes, mime_type=mime_type, user_id=user_id)

    return jsonify({"success": True, "data": {"task_id": task_id}, "error": None}), 202


@api_bp.route("/vision/extract/<task_id>", methods=["GET"])
@require_auth
def get_extract_status(task_id: str):
    """Poll for the status of an asynchronous cover extraction task."""
    user_id = getattr(request, "user_id", None)
    result = get_task_result(task_id, user_id=user_id)

    if not result:
        return jsonify({"success": False, "data": None, "error": "Task not found"}), 404

    if result["status"] == "completed":
        data = result["result"]
        if data is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "data": None,
                        "error": "Vision extraction failed. Fallback methods unconfigured or failed.",
                    }
                ),
                503,
            )
        return jsonify({"success": True, "data": data, "error": None}), 200

    if result["status"] == "failed":
        status_code = 503 if "Vision extraction failed" in str(result.get("error", "")) else 500
        return jsonify({"success": False, "data": None, "error": result["error"]}), status_code

    # Task is pending or processing
    return jsonify({"success": True, "data": {"status": result["status"]}, "error": None}), 202
