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
import os

from flask import jsonify, request
from PIL import Image

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.core.ingest import IngestService
from app.db.models import Item, Manifestation, db
from app.utils.vision import extract_metadata_from_cover

# Maximum allowed upload size for cover images (10 MB)
_MAX_COVER_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


@api_bp.route("/scan", methods=["POST"])
@require_auth
def scan_barcode():
    """Scan a barcode and add the corresponding item to the authenticated user's collection.

    Request body (JSON):
        barcode (str): The ISBN or other barcode value to look up.

    Returns:
        201 – ``{"message", "item_id", "manifestation_id", "title", "is_new_manifestation"}``
        400 – barcode missing or invalid
        404 – barcode could not be resolved to a manifestation
        503 – upstream network error during metadata lookup
    """
    data = request.get_json()
    barcode = data.get("barcode")

    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400

    is_new_manifestation = False
    manifestation = Manifestation.query.filter(Manifestation.meta.op("->>")("isbn") == barcode).first()  # type: ignore[attr-defined]

    if not manifestation:
        try:
            manifestation = IngestService.ingest_from_isbn(barcode)
            is_new_manifestation = True
        except ValueError as e:
            return jsonify({"error": f"Invalid barcode or ISBN: {str(e)}"}), 400
        except ConnectionError as e:
            return jsonify({"error": f"Network error while fetching metadata: {str(e)}"}), 503
        except Exception as e:  # pylint: disable=broad-exception-caught
            return jsonify({"error": f"Failed to find or ingest metadata for barcode: {str(e)}"}), 404

    if not manifestation:
        return jsonify({"error": "Could not resolve barcode"}), 404

    new_item = Item(manifestation_id=manifestation.id, owner_id=request.user_id, status="available")
    db.session.add(new_item)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Item successfully added to your collection",
                "item_id": new_item.id,
                "manifestation_id": manifestation.id,
                "title": manifestation.title,
                "is_new_manifestation": is_new_manifestation,
            }
        ),
        201,
    )


@api_bp.route("/vision/extract", methods=["POST"])
@require_auth
def extract_from_cover():
    # pylint: disable=too-many-return-statements
    """Extract book Title and Authors from an uploaded cover image using Gemini Vision.

    Accepts a multipart/form-data ``POST`` with a ``cover`` file field.
    The image is passed to the Gemini Vision API which returns the title and
    author(s) extracted from the cover artwork.

    **Supported image types:** JPEG, PNG, WebP (max 10 MB).

    **Setup:** Requires the ``GEMINI_API_KEY`` environment variable to be set.
    See ``docs/COVERS_SETUP.md`` → *Vision-based Metadata Extraction* for details.

    Request form fields:
        cover (file): The cover image to analyse.

    Returns:
        200 – ``{"success": true, "data": {"Title": str, "Authors": [str]}, "error": null}``
        400 – missing file, empty filename, invalid extension, oversized or corrupt image
        401 – authentication required (handled by ``@require_auth``)
        503 – Gemini API key not configured or upstream call failed
    """
    if "cover" not in request.files:
        return jsonify({"success": False, "data": None, "error": "No file provided"}), 400

    file = request.files["cover"]
    if not file.filename:
        return jsonify({"success": False, "data": None, "error": "No selected file"}), 400

    # --- Extension validation ---
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

    # --- Size validation (Content-Length header, fast path) ---
    if request.content_length and request.content_length > _MAX_COVER_SIZE:
        return jsonify({"success": False, "data": None, "error": "File too large. Max size: 10 MB"}), 413

    # --- Size validation (seek-based, catches missing Content-Length) ---
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > _MAX_COVER_SIZE:
        return jsonify({"success": False, "data": None, "error": "File too large. Max size: 10 MB"}), 413

    # --- PIL content verification ---
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except (OSError, SyntaxError):
        return jsonify({"success": False, "data": None, "error": "Invalid or corrupted image file"}), 400

    # --- Vision extraction ---
    image_bytes = file.read()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    result = extract_metadata_from_cover(image_bytes, mime_type=mime_type)

    if result is None:
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": (
                        "Vision extraction is unavailable. "
                        "Ensure GEMINI_API_KEY is configured. "
                        "See docs/COVERS_SETUP.md for setup instructions."
                    ),
                }
            ),
            503,
        )

    return jsonify({"success": True, "data": result, "error": None}), 200
