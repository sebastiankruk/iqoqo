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
"""API routes for extracting and exposing generic taxonomies."""

from flask import Response, g, jsonify
from sqlalchemy import func, text

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.db.models import Item, db


@api_bp.route("/taxonomies", methods=["GET"])
@require_auth
def get_taxonomies() -> Response | tuple[Response, int]:
    """
    Extract distinct tags, collections, genres, and publishers from the user's items.
    Relies on PostgreSQL JSONB functions to extract arrays and unnest them.
    """
    user_id = getattr(g, "user_id", None)

    def get_jsonb_array_elements(field_name: str):
        return (
            db.session.query(
                func.jsonb_array_elements_text(func.coalesce(Item.meta.op("->")(field_name), text("'[]'::jsonb"))).label("element")
            )
            .filter(Item.owner_id == user_id)
            .distinct()
            .all()
        )

    def get_jsonb_string_elements(field_name: str):
        return (
            db.session.query(Item.meta.op("->>")(field_name).label("element"))
            .filter(Item.owner_id == user_id, Item.meta.op("->>")(field_name) is not None)
            .distinct()
            .all()
        )

    try:
        tags = [row.element for row in get_jsonb_array_elements("tags")]
        genres = [row.element for row in get_jsonb_array_elements("genres")]
        collections = [row.element for row in get_jsonb_array_elements("collections")]
        publishers = [row.element for row in get_jsonb_string_elements("publisher")]

        return jsonify(
            {
                "success": True,
                "data": {
                    "tags": sorted(tags),
                    "genres": sorted(genres),
                    "collections": sorted(collections),
                    "publishers": sorted(publishers),
                },
            }
        )
    except Exception:
        return jsonify({"success": False, "error": "Failed to load taxonomies"}), 500
