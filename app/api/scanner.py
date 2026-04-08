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
import io

from flask import jsonify, request
from PIL import Image

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import require_auth, require_permission
from app.core.ingest import IngestService
from app.core.permissions import ItemPermissions
from app.core.tasks import get_task_result, submit_task
from app.db.models import Item, Manifestation, db
from app.utils.bgg import fetch_bgg_metadata
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import canonicalize_isbn, fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import fetch_video_metadata
from app.utils.upc import fetch_upc_metadata
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


@api_bp.route("/lookup/<barcode>", methods=["GET"])
@require_auth
def lookup_barcode_preview(barcode: str):
    """Generic barcode lookup for preview (books, audio, video, games)."""
    format_hint = request.args.get("format")

    # Check DB first
    # pylint: disable=singleton-comparison
    manifestation = Manifestation.query.filter(
        (Manifestation.meta["isbn"].as_string() == barcode) | (Manifestation.meta["barcode"].as_string() == barcode)
    ).first()

    if manifestation and manifestation.meta:
        title = manifestation.meta.get("title") or manifestation.meta.get("Title")
        if title:
            return jsonify({"success": True, "data": manifestation.meta, "error": None}), 200

    meta = None
    is_book = barcode.startswith("978") or barcode.startswith("979") or len(barcode) == 10

    # Route based on format hint first, fallback to heuristics
    if format_hint in ("video", "dvd", "bluray", "movie"):
        meta = fetch_video_metadata(barcode)
    elif format_hint in ("game", "boardgame"):
        meta = fetch_bgg_metadata(barcode)
    elif format_hint in ("puzzle", "jigsaw"):
        meta = fetch_upc_metadata(barcode)
    elif format_hint in ("audio", "cd", "vinyl", "sound"):
        try:
            meta = fetch_discogs_metadata(barcode) or fetch_audio_metadata(barcode)
        except Exception:  # pylint: disable=broad-except
            pass
    elif is_book or format_hint in ("book", "text"):
        canonical = canonicalize_isbn(barcode)
        if canonical:
            meta = fetch_isbn_metadata(canonical)

        # Fallback to audio if book fails
        if not meta:
            try:
                meta = fetch_discogs_metadata(barcode) or fetch_audio_metadata(barcode)
            except Exception:  # pylint: disable=broad-except
                pass
    else:
        # No format hint: auto-fallback strategy for non-ISBN barcodes
        # Try audio sources first (UPC/EAN codes commonly map to audio)
        try:
            meta = fetch_discogs_metadata(barcode) or fetch_audio_metadata(barcode)
        except Exception:  # pylint: disable=broad-except
            pass

        # Fallback to book if audio fails
        if not meta:
            canonical = canonicalize_isbn(barcode)
            if canonical:
                meta = fetch_isbn_metadata(canonical)

        # Final fallback to video/game if all else fails
        if not meta:
            meta = fetch_video_metadata(barcode) or fetch_bgg_metadata(barcode)

    if not meta:
        return jsonify({"success": False, "data": None, "error": f"No metadata found for barcode {barcode}"}), 404

    # Ensure frontend gets normalized keys for preview
    if "title" not in meta:
        meta["title"] = meta.get("Title") or "Unknown Title"
    if "cover_url" not in meta:
        meta["cover_url"] = meta.get("thumb") or meta.get("cover")
    if "author" not in meta:
        meta["author"] = (
            meta.get("artist") or meta.get("Artist") or meta.get("manufacturer") or meta.get("brand") or meta.get("authors", [None])[0]
        )

    return jsonify({"success": True, "data": meta, "error": None}), 200


@api_bp.route("/scan", methods=["POST"])
@require_auth
def scan_barcode():
    # pylint: disable=too-many-return-statements
    """Scan a barcode and add the corresponding item to the authenticated user's collection."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    barcode = data.get("barcode")
    format_hint = data.get("format")

    if not barcode:
        return jsonify({"success": False, "data": None, "error": "Barcode is required"}), 400

    is_new_manifestation = False

    # pylint: disable=singleton-comparison
    manifestation = Manifestation.query.filter(
        (Manifestation.meta["isbn"].as_string() == barcode) | (Manifestation.meta["barcode"].as_string() == barcode)
    ).first()

    if not manifestation:
        try:
            if format_hint in ("audio", "cd", "vinyl", "sound"):
                manifestation = IngestService.ingest_audio_from_barcode(barcode)
            elif format_hint in ("video", "dvd", "bluray", "movie"):
                manifestation = IngestService.ingest_video_from_barcode(barcode)
            elif format_hint in ("game", "boardgame"):
                manifestation = IngestService.ingest_game_from_barcode(barcode)
            elif format_hint in ("puzzle", "jigsaw"):
                manifestation = IngestService.ingest_puzzle_from_barcode(barcode)
            elif format_hint in ("book", "text"):
                manifestation = IngestService.ingest_from_isbn(barcode)
            else:
                # Auto-fallback strategy
                is_isbn_like = len(barcode) == 13 and (barcode.startswith("978") or barcode.startswith("979")) or len(barcode) == 10
                if is_isbn_like:
                    try:
                        manifestation = IngestService.ingest_from_isbn(barcode)
                    except ValueError:
                        manifestation = IngestService.ingest_audio_from_barcode(barcode)
                else:
                    try:
                        manifestation = IngestService.ingest_audio_from_barcode(barcode)
                    except ValueError:
                        try:
                            manifestation = IngestService.ingest_video_from_barcode(barcode)
                        except ValueError:
                            manifestation = IngestService.ingest_from_isbn(barcode)

            is_new_manifestation = True
        except ValueError as e:
            return jsonify({"success": False, "data": None, "error": f"Invalid barcode or not found: {str(e)}"}), 400
        except ConnectionError as e:
            return jsonify({"success": False, "data": None, "error": f"Network error while fetching metadata: {str(e)}"}), 503
        except Exception as e:  # pylint: disable=broad-except
            return jsonify({"success": False, "data": None, "error": f"Failed to find or ingest metadata for barcode: {str(e)}"}), 404

    if not manifestation:
        return jsonify({"success": False, "data": None, "error": "Could not resolve barcode"}), 404

    new_item = Item(manifestation_id=manifestation.id, owner_id=request.user_id, status="available")
    db.session.add(new_item)
    db.session.commit()

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
                        manifestation.meta.get("author") or manifestation.meta.get("authors", [None])[0]
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
@require_permission(ItemPermissions.LLM_GENERATE_METADATA)
def extract_from_cover():
    # pylint: disable=too-many-return-statements
    """Submit a cover image for asynchronous metadata extraction.

    Returns:
        202 - ``{"success": true, "data": {"task_id": str}, "error": null}``
    """
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
    user_id = getattr(request, "user_id", None)

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
