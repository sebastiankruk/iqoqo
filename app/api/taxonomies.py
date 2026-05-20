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
from sqlalchemy.exc import SQLAlchemyError

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.db.core import Item, ItemTag, Manifestation, Tag, UserCollection, Work, db


@api_bp.route("/taxonomies", methods=["GET"])
@require_auth
def get_taxonomies() -> Response | tuple[Response, int]:
    """
    Extract distinct tags, collections, genres, and publishers.
    - Tags: Tags attached to the current user's items.
    - Collections: All collection names for the current user.
    - Publishers: Publishers from the current user's items.
    - Genres: Genres present in works owned by the current user.
    """
    user_id = getattr(g, "user_id", None)

    try:
        # Tags scoped to current user's items
        tags_query = (
            db.session.query(Tag.name)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .join(Item, Item.id == ItemTag.item_id)
            .filter(Item.owner_id == user_id)
            .distinct()
            .all()
        )
        tags = sorted([t[0] for t in tags_query if t[0]])

        # User's collection names
        collections_query = db.session.query(UserCollection.name).filter(UserCollection.owner_id == user_id).distinct().all()
        collections = sorted([c[0] for c in collections_query if c[0]])

        # Publishers scoped to current user's items
        publishers_query = (
            db.session.query(Manifestation.publisher)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .filter(
                Item.owner_id == user_id,
                Manifestation.publisher.isnot(None),
                Manifestation.publisher != "",
            )
            .distinct()
            .all()
        )
        publishers = sorted([p[0].strip() for p in publishers_query if p[0] and p[0].strip()])

        # Genres extracted from Works linked to the current user's items
        works = (
            db.session.query(Work)
            .join(Work.expressions)
            .join(Manifestation)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .filter(Item.owner_id == user_id)
            .distinct()
            .all()
        )
        genres_set: set[str] = set()
        for w in works:
            if w.meta:
                raw = w.meta.get("genres") or w.meta.get("genre")
                if isinstance(raw, list):
                    for g_val in raw:
                        if isinstance(g_val, str) and g_val.strip():
                            genres_set.add(g_val.strip())
                elif isinstance(raw, str) and raw.strip():
                    genres_set.add(raw.strip())
        genres = sorted(genres_set)

        return jsonify(
            {
                "success": True,
                "data": {
                    "tags": tags,
                    "genres": genres,
                    "collections": collections,
                    "publishers": publishers,
                },
            }
        )
    except SQLAlchemyError as e:
        import logging

        logging.getLogger(__name__).error(f"Error fetching taxonomies: {e}")
        return jsonify({"success": False, "error": "Failed to load taxonomies"}), 500
