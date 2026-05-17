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
from sqlalchemy.exc import SQLAlchemyError

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

    if db.engine.dialect.name == "sqlite":
        try:
            items = db.session.query(Item).filter(Item.owner_id == user_id).all()
            tags_set = set()
            genres_set = set()
            collections_set = set()
            publishers_set = set()
            for item in items:
                meta = item.meta or {}
                # Extract arrays
                for t in meta.get("tags", []):
                    if isinstance(t, str) and t.strip():
                        tags_set.add(t.strip())
                for gen in meta.get("genres", []):
                    if isinstance(gen, str) and gen.strip():
                        genres_set.add(gen.strip())
                for col in meta.get("collections", []):
                    if isinstance(col, str) and col.strip():
                        collections_set.add(col.strip())
                # Extract string
                pub = meta.get("publisher")
                if isinstance(pub, str) and pub.strip():
                    publishers_set.add(pub.strip())

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "tags": sorted(tags_set),
                        "genres": sorted(genres_set),
                        "collections": sorted(collections_set),
                        "publishers": sorted(publishers_set),
                    },
                }
            )
        except SQLAlchemyError:
            return jsonify({"success": False, "error": "Failed to load taxonomies"}), 500

    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import cast

    def get_jsonb_array_elements(field_name: str):
        return (
            db.session.query(
                func.jsonb_array_elements_text(
                    func.coalesce(cast(Item.meta, JSONB).op("->")(field_name), text("'[]'::jsonb"))
                ).label("element")
            )
            .filter(Item.owner_id == user_id)
            .distinct()
            .all()
        )

    def get_jsonb_string_elements(field_name: str):
        return (
            db.session.query(cast(Item.meta, JSONB).op("->>")(field_name).label("element"))
            .filter(Item.owner_id == user_id, cast(Item.meta, JSONB).op("->>")(field_name).isnot(None))
            .distinct()
            .all()
        )

    try:
        tags = [row.element for row in get_jsonb_array_elements("tags") if row.element]
        genres = [row.element for row in get_jsonb_array_elements("genres") if row.element]
        collections = [row.element for row in get_jsonb_array_elements("collections") if row.element]
        publishers = [row.element for row in get_jsonb_string_elements("publisher") if row.element]

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
    except SQLAlchemyError:
        return jsonify({"success": False, "error": "Failed to load taxonomies"}), 500
