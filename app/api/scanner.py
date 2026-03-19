"""Handles Barcode lookups"""

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
from flask import jsonify, request

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.core.ingest import IngestService
from app.db.models import Item, Manifestation, db


@api_bp.route("/scan", methods=["POST"])
@require_auth
def scan_barcode():
    data = request.get_json()
    barcode = data.get("barcode")

    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400

    is_new_manifestation = False
    manifestation = Manifestation.query.filter(Manifestation.meta.op("->>")("isbn") == barcode).first()

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
def extract_from_cover():
    """Extract Title/Author from an uploaded cover image using OCR/Vision."""
    if "cover" not in request.files:
        return jsonify({"success": False, "data": None, "error": "No file provided"}), 400

    file = request.files["cover"]
    if not file.filename:
        return jsonify({"success": False, "data": None, "error": "No selected file"}), 400

    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return jsonify({"success": False, "data": None, "error": "Invalid file type. Allowed: png, jpg, jpeg, webp"}), 400

    # TODO: Integrate external AI/Vision API (e.g., Google Vision/Gemini/Tesseract) here
    # Mock return extracting metadata from an image
    extracted_data = {
        "Title": "Extracted Title",
        "Authors": ["Extracted Author"]
    }

    return jsonify({"success": True, "data": extracted_data, "error": None}), 200
