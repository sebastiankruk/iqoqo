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

    manifestation = Manifestation.query.filter(Manifestation.meta.op("->>")("isbn") == barcode).first()

    if not manifestation:
        try:
            manifestation = IngestService.ingest_from_isbn(barcode)
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
                "is_new_manifestation": not manifestation,
            }
        ),
        201,
    )
