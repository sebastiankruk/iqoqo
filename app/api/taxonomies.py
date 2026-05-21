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
    Supports a 'scope' query parameter:
    - `scope=user`: (default for backward compatibility if needed, but let's default to global per user request)
    - `scope=global`: Returns all available values regardless of the user.
    """
    from flask import request

    user_id = getattr(g, "user_id", None)
    scope = request.args.get("scope", "global")

    try:
        # 1. Tags & Collections (Scope-dependent)
        if scope == "user":
            tags_query = (
                db.session.query(Tag.name)
                .join(ItemTag, ItemTag.tag_id == Tag.id)
                .join(Item, Item.id == ItemTag.item_id)
                .filter(Item.owner_id == user_id)
                .distinct()
                .all()
            )
            collections_query = db.session.query(UserCollection.name).filter(UserCollection.owner_id == user_id).distinct().all()
        else:
            tags_query = db.session.query(Tag.name).distinct().all()
            collections_query = db.session.query(UserCollection.name).distinct().all()

        # 2. Publishers & Genres (Always Global, per FRBR tier logic)
        publishers_query = (
            db.session.query(Manifestation.publisher)
            .filter(
                Manifestation.publisher.isnot(None),
                Manifestation.publisher != "",
            )
            .distinct()
            .all()
        )

        work_ids = db.session.query(Work.id).distinct().all()
        w_ids = [r[0] for r in work_ids]

        tags = sorted([t[0] for t in tags_query if t[0]])
        collections = sorted([c[0] for c in collections_query if c[0]])
        publishers = sorted([p[0].strip() for p in publishers_query if p[0] and p[0].strip()])

        genres_set: set[str] = set()
        if w_ids:
            works_meta = db.session.query(Work.meta).filter(Work.id.in_(w_ids)).all()
            for row in works_meta:
                meta = row[0]
                if meta:
                    raw = meta.get("genres") or meta.get("genre")
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
