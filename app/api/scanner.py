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
import uuid
from typing import Any

from flask import Response, current_app, g, jsonify, request
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import or_

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import require_auth, require_permission
from app.api.schemas import ScanBarcodeSchema
from app.core.ingest import IngestService
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.core.tasks import get_task_result, submit_task
from app.db.models import Expression, Item, Manifestation, ScanTelemetry, UserWorkIntent, db
from app.strategies import LookupStrategyFactory
from app.utils.discogs import fetch_discogs_by_id, fetch_discogs_candidates
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
    barcode: str | None,
    format_hint: str | None,
    provider: str,
    status: str,
    manifestation_id: int | None = None,
    raw_request_url: str | None = None,
) -> None:
    """Helper to persist a scan-lookup record safely."""
    try:
        effective_barcode = barcode
        effective_status = status
        if barcode and len(barcode) > 128:
            current_app.logger.warning("Barcode too long (%d chars), recording truncated telemetry", len(barcode))
            effective_barcode = f"{barcode[:120]}...({len(barcode)})"
            effective_status = "rejected_oversized"

        # Create a savepoint to prevent rollback of outer transactions
        with db.session.begin_nested():
            telemetry = ScanTelemetry(
                barcode=effective_barcode,
                format_hint=format_hint,
                provider=provider,
                status=effective_status,
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
    from app.core.taxonomy import CATEGORY_INGEST_METHOD

    ingest_map = {cat: getattr(IngestService, method) for cat, method in CATEGORY_INGEST_METHOD.items()}

    current_app.logger.info("Ingesting barcode=%s format_hint=%s category_hint=%s", barcode, format_hint, category_hint)

    if category_hint in ingest_map:
        result: Manifestation = ingest_map[category_hint](barcode)
        return result

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
        IngestService.ingest_from_isbn,
    ]:
        try:
            return ingest_func(barcode)
        except ValueError:
            continue

    raise ValueError("Exhausted all ingestion methods")


@api_bp.route("/lookup/<query>", methods=["GET"])
@require_auth
@limiter.limit("30 per minute", override_defaults=True)
def lookup_barcode_preview(query: str) -> Response | tuple[Response, int]:
    """Generic identifier lookup for preview (barcode, ISBN, or name hash)."""
    # Enforce query length cap to prevent upstream API quota exhaustion
    MAX_QUERY_LENGTH = 128
    query = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", query)  # Strip control characters
    if len(query) > MAX_QUERY_LENGTH:
        return jsonify({"error": f"Query too long (max {MAX_QUERY_LENGTH} characters)"}), 400

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
                cand = _normalize_preview_meta(cand, format_hint)
                cand["manifestation_id"] = m.id
                cand["already_in_db"] = True
                cand["already_in_collection"] = m.id in owned_ids
                cand["item_id"] = owned_ids.get(m.id)
                candidates.append(cand)

        data = dict(manifestation.meta)
        data = _normalize_preview_meta(data, format_hint)

        # If the DB metadata is hopelessly broken (legacy ingest bug),
        # pretend we didn't find it so we can re-fetch rich data from external APIs.
        if data.get("title") == "Unknown Title" and not data.get("author"):
            manifestation = None
        else:
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

    # For non-barcode text queries, fetch candidates based on format
    if not is_barcode:
        candidates = []
        if category_hint == "music" or format_hint in (None, ""):
            candidates.extend(fetch_discogs_candidates(query))

        if category_hint == "book" or format_hint in (None, ""):
            from app.utils.isbn import fetch_google_books_candidates

            candidates.extend(fetch_google_books_candidates(query))

        if len(candidates) >= 1:
            response_data = copy.deepcopy(candidates[0])
            response_data["candidates"] = candidates
            response_data["identifier"] = query
            response_data["already_in_collection"] = False
            response_data["item_id"] = None
            response_data["data_source"] = response_data.get("data_source", "search")
            _record_scan_telemetry(query, format_hint, "search", "success")
            return jsonify({"success": True, "data": response_data, "error": None}), 200

    # Leverage the Strategy Pattern for format-specific metadata lookups
    # (e.g., ISBN for books, UPC for music/movies, BGG for games)
    strategy = LookupStrategyFactory.get_strategy(category_hint)
    meta, provider = strategy.lookup(barcode, query)

    if not meta:
        _record_scan_telemetry(barcode, format_hint, provider=format_hint or "unknown", status="failed")
        return jsonify({"success": False, "data": None, "error": f"No metadata found for barcode {barcode}"}), 404

    meta = _normalize_preview_meta(meta, format_hint)

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


def _normalize_preview_meta(meta: dict[str, Any], format_hint: str | None = None) -> dict[str, Any]:
    """Normalize metadata from external providers for the frontend preview."""
    # 1. Title
    if "title" not in meta:
        meta["title"] = meta.get("Title") or meta.get("title") or "Unknown Title"

    # 2. Authors list
    raw_authors = meta.get("Authors") or meta.get("authors")
    normalized_authors: list[str] = []
    if isinstance(raw_authors, list):
        for a in raw_authors:
            if isinstance(a, dict):
                name = a.get("name")
                if name:
                    normalized_authors.append(str(name))
            elif a:
                normalized_authors.append(str(a))
    elif isinstance(raw_authors, str) and raw_authors:
        normalized_authors.append(raw_authors)
    elif isinstance(raw_authors, dict):
        name = raw_authors.get("name")
        if name:
            normalized_authors.append(str(name))

    if normalized_authors:
        meta["Authors"] = normalized_authors
    else:
        meta.pop("Authors", None)
    meta.pop("authors", None)

    # 3. Resolve single "author" string
    if "author" not in meta or not meta["author"]:
        potential_author = (
            meta.get("artist")
            or meta.get("Artist")
            or meta.get("director")
            or meta.get("Director")
            or meta.get("designer")
            or meta.get("Designer")
            or meta.get("manufacturer")
            or meta.get("brand")
        )
        if not potential_author and normalized_authors:
            potential_author = normalized_authors[0]

        if isinstance(potential_author, dict):
            meta["author"] = potential_author.get("name")
        elif potential_author:
            meta["author"] = str(potential_author)
        else:
            meta["author"] = None
    elif isinstance(meta["author"], dict):
        meta["author"] = meta["author"].get("name")
    else:
        meta["author"] = str(meta["author"])

    # 4. Cover URL
    if "cover_url" not in meta or not meta["cover_url"]:
        cover_val = meta.get("cover_url") or meta.get("thumb") or meta.get("cover") or meta.get("thumbnail")
        if isinstance(cover_val, dict):
            meta["cover_url"] = cover_val.get("large") or cover_val.get("medium") or cover_val.get("small")
        elif isinstance(cover_val, list) and len(cover_val) > 0:
            meta["cover_url"] = cover_val[0]
        else:
            meta["cover_url"] = cover_val

    # 5. Format
    if "format" not in meta or not meta["format"]:
        if format_hint:
            from app.core.taxonomy import FORMAT_TO_CATEGORY
            from app.db.core import MediaFormat

            canonical_format = format_hint if format_hint in FORMAT_TO_CATEGORY else format_hint.upper()

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
            meta["format"] = hint_to_format.get(format_hint, canonical_format)
        else:
            meta["format"] = "BOOK"

    return meta


def _validate_scan_request(payload: ScanBarcodeSchema) -> str | None:
    """Validate barcode and collection status."""
    barcode = payload.barcode
    manifestation_id = payload.manifestation_id
    collection_status = payload.collection_status

    from app.core.taxonomy import COLLECTION_STATUSES

    if not barcode and not manifestation_id:
        return "Barcode or Manifestation ID is required"
    if collection_status not in COLLECTION_STATUSES:
        return f"Invalid collection_status. Valid values: {list(COLLECTION_STATUSES)}"
    return None


def _parse_scan_payload(req) -> tuple[ScanBarcodeSchema | None, Response | tuple[Response, int] | None]:
    """Parse JSON payload into ScanBarcodeSchema."""
    payload_json = req.get_json(silent=True)
    if not isinstance(payload_json, dict):
        return None, invalid_json_payload_response()

    try:
        payload = ScanBarcodeSchema(**payload_json)
        # Normalize legacy 'wishlist' to canonical 'wish_list'
        STATUS_ALIASES = {"wishlist": "wish_list"}
        if payload.collection_status in STATUS_ALIASES:
            payload.collection_status = STATUS_ALIASES[payload.collection_status]
        return payload, None
    except (ValidationError, TypeError) as e:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid payload",
                    "details": str(e),
                }
            ),
            400,
        )


def _parse_and_validate_scan(req) -> tuple[ScanBarcodeSchema | None, Response | tuple[Response, int] | None]:
    """Consolidated helper to parse and validate scan request."""
    payload, err = _parse_scan_payload(req)
    if err:
        return None, err
    assert payload is not None

    validation_error = _validate_scan_request(payload)
    if validation_error:
        return None, (jsonify({"success": False, "data": None, "error": validation_error}), 400)

    return payload, None


def _get_manifestation_author(manifestation: Manifestation) -> str | None:
    """Helper to safely extract the author string from a manifestation's metadata or direct property."""
    if not manifestation.meta:
        return manifestation.author

    author = manifestation.meta.get("author")
    if author:
        if isinstance(author, dict):
            val = author.get("name")
            return str(val) if val is not None else None
        return str(author)

    authors = manifestation.meta.get("Authors") or manifestation.meta.get("authors")
    if authors and isinstance(authors, list):
        first = authors[0]
        if isinstance(first, dict):
            val = first.get("name")
            return str(val) if val is not None else None
        return str(first) if first is not None else None

    return None


def _scan_to_wishlist(
    barcode: str | None,
    manifestation: Manifestation,
    format_hint: str | None,
    is_new_manifestation: bool,
    default_progress: str,
    user_id: uuid.UUID | None,
) -> tuple[Response, int]:
    """Helper to save intent to wishlist."""
    work = manifestation.expression.work if (manifestation.expression and manifestation.expression.work) else None
    if not work:
        return jsonify({"success": False, "data": None, "error": "Work not found for manifestation"}), 500

    # Check if intent already exists
    intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work.id).first()
    if not intent:
        intent = UserWorkIntent(
            user_id=user_id,
            work_id=work.id,
            status=default_progress,
        )
        db.session.add(intent)
        db.session.flush()

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
        barcode or manifestation.title,
        format_hint,
        provider=format_hint or "ingest",
        status="success",
        manifestation_id=manifestation.id,
    )

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "message": "Item successfully added to your collection",
                    "identifier_label": "ISBN" if (manifestation.meta.get("isbn") or "").strip() else "Barcode",
                    "identifier_value": manifestation.meta.get("isbn") or manifestation.meta.get("barcode"),
                    "item_id": None,
                    "intent_id": intent.id,
                    "manifestation_id": manifestation.id,
                    "title": (
                        manifestation.meta.get("title") or manifestation.meta.get("Title") if manifestation.meta else manifestation.title
                    ),
                    "author": _get_manifestation_author(manifestation),
                    "cover_url": (
                        manifestation.meta.get("cover_url") or manifestation.meta.get("thumb")
                        if manifestation.meta
                        else manifestation.cover_url
                    ),
                    "is_new_manifestation": is_new_manifestation,
                    "action": "added_to_wishlist",
                },
                "error": None,
            }
        ),
        201,
    )


def _scan_to_library(
    barcode: str | None,
    manifestation: Manifestation,
    format_hint: str | None,
    collection_status: str,
    payload: ScanBarcodeSchema,
    is_new_manifestation: bool,
    default_progress: str,
    user_id: uuid.UUID | None,
) -> tuple[Response, int]:
    """Helper to save physical item to library."""
    # Assign dynamically passed collection_status (Library vs Wishlist)
    new_item = Item(
        manifestation_id=manifestation.id,
        owner_id=user_id,
        status=default_progress,
        collection_status=collection_status,
        lent_to_user_id=uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None,
        lent_to_name=payload.lent_to_name,
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
                    "author": _get_manifestation_author(manifestation),
                    "cover_url": (
                        manifestation.meta.get("cover_url") or manifestation.meta.get("thumb")
                        if manifestation.meta
                        else manifestation.cover_url
                    ),
                    "is_new_manifestation": is_new_manifestation,
                    "action": "added_to_inventory",
                },
                "error": None,
            }
        ),
        201,
    )


@api_bp.route("/scan", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
@limiter.limit("20 per minute", override_defaults=True)
def scan_barcode() -> Response | tuple[Response, int]:  # pylint: disable=too-many-return-statements
    """Scan a barcode and add the corresponding item to the authenticated user's collection."""
    payload, err = _parse_and_validate_scan(request)
    if err:
        return err
    assert payload is not None

    barcode: str | None = payload.barcode
    manifestation_id: int | None = payload.manifestation_id
    format_hint: str | None = payload.format
    collection_status: str | None = payload.collection_status
    policy: str | None = payload.policy
    assert collection_status is not None

    is_new_manifestation = False
    manifestation = None
    if manifestation_id:
        manifestation = db.session.get(Manifestation, manifestation_id)

    if not manifestation and (barcode or payload.meta):
        manifestation = _find_locally(barcode) if barcode else None
        if not manifestation:
            try:
                from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY

                category_hint = FORMAT_ALIAS_TO_CATEGORY.get(format_hint) if format_hint else None

                # Support pure numeric Discogs Release IDs
                is_discogs_numeric = False
                if barcode and barcode.isdigit() and len(barcode) <= 8:
                    is_discogs_numeric = True

                if is_discogs_numeric and barcode and (category_hint == "music" or format_hint is None):
                    meta = fetch_discogs_by_id(barcode)
                    if meta:
                        manifestation = IngestService.ingest_from_meta(meta)

                if not manifestation and payload.meta:
                    manifestation = IngestService.ingest_from_meta(payload.meta)

                if not manifestation and barcode:
                    manifestation = _ingest_by_hint(barcode, category_hint, format_hint)

                is_new_manifestation = True

            except (ValueError, ConnectionError, KeyError, AttributeError, TypeError, OSError, RuntimeError) as e:
                _record_scan_telemetry(barcode, format_hint, provider=format_hint or "ingest", status="failed")
                err_msg = str(e)
                code = 404
                if isinstance(e, ConnectionError):
                    code = 503
                elif isinstance(e, ValueError):
                    code = 400
                return jsonify({"success": False, "data": None, "error": f"Resolution failed: {err_msg}"}), code

    if not manifestation:
        _record_scan_telemetry(barcode, format_hint, provider=format_hint or "ingest", status="failed")
        return jsonify({"success": False, "data": None, "error": "Could not resolve barcode"}), 404

    from app.db.core import CATEGORY_PROGRESS_STATUSES

    content_type = manifestation.expression.content_type if manifestation.expression else "text"
    statuses = CATEGORY_PROGRESS_STATUSES.get(content_type, ("want_to_read",))
    if policy == "wishlist" or collection_status == "wish_list":
        default_progress = next((s for s in statuses if s.startswith("want_to_")), statuses[0])
    else:
        default_progress = statuses[0]

    if collection_status == "lent":
        if not payload.lent_to_user_id and not (payload.lent_to_name and payload.lent_to_name.strip()):
            return jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

    user_id = getattr(g, "user_id", None)

    if policy == "catalog":
        _record_scan_telemetry(
            barcode or manifestation.title,
            format_hint,
            provider=format_hint or "ingest",
            status="success",
            manifestation_id=manifestation.id,
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "message": "Item successfully added to catalog",
                        "identifier_label": "ISBN" if (manifestation.meta.get("isbn") or "").strip() else "Barcode",
                        "identifier_value": manifestation.meta.get("isbn") or manifestation.meta.get("barcode"),
                        "item_id": None,
                        "intent_id": None,
                        "manifestation_id": manifestation.id,
                        "title": (
                            manifestation.meta.get("title") or manifestation.meta.get("Title")
                            if manifestation.meta
                            else manifestation.title
                        ),
                        "author": _get_manifestation_author(manifestation),
                        "cover_url": (
                            manifestation.meta.get("cover_url") or manifestation.meta.get("thumb")
                            if manifestation.meta
                            else manifestation.cover_url
                        ),
                        "is_new_manifestation": is_new_manifestation,
                        "action": "cataloged",
                    },
                    "error": None,
                }
            ),
            201,
        )

    if policy == "wishlist" or collection_status == "wish_list":
        return _scan_to_wishlist(barcode, manifestation, format_hint, is_new_manifestation, default_progress, user_id)

    return _scan_to_library(
        barcode, manifestation, format_hint, collection_status, payload, is_new_manifestation, default_progress, user_id
    )


@api_bp.route("/vision/extract", methods=["POST"])
@require_auth
@require_permission(PermissionName.LLM_GENERATE_METADATA)
def extract_from_cover():
    """Submit a cover image for asynchronous metadata extraction."""
    file = request.files.get("cover")
    if not file or not file.filename:
        return jsonify({"success": False, "data": None, "error": "No file provided"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "data": None, "error": f"Invalid file type: {ext}"}), 400

    too_large = request.content_length and request.content_length > _MAX_COVER_SIZE
    image_bytes = None if too_large else _read_bounded(file, _MAX_COVER_SIZE)
    if image_bytes is None:
        return jsonify({"success": False, "data": None, "error": "File too large"}), 413

    try:
        Image.open(io.BytesIO(image_bytes)).verify()
    except (OSError, SyntaxError):
        return jsonify({"success": False, "data": None, "error": "Invalid or corrupted image file"}), 400

    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")
    task_id = submit_task(extract_metadata_from_cover, image_bytes, mime_type=mime_type, user_id=getattr(g, "user_id", None))

    if task_id is None:
        return jsonify({"success": False, "data": None, "error": "Background queue unavailable. Please try again later."}), 503

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
