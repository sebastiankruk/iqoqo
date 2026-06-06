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
from app.db.core import Expression, Item, ItemTag, Manifestation, Tag, UserCollection, Work, db


@api_bp.route("/taxonomies", methods=["GET"])
@require_auth
def get_taxonomies() -> Response | tuple[Response, int]:
    """
    Extract distinct tags, collections, genres, and publishers.
    Supports a 'scope' query parameter:
    - `scope=user`: (default for backward compatibility if needed, but let's default to global per user request)
    - `scope=global`: Returns all available values regardless of the user.

    Cross-faceted narrowing: pass category, format, genre, or collection_status to narrow results.
    """
    from flask import request

    user_id = getattr(g, "user_id", None)
    scope = request.args.get("scope", "global")
    # Cross-facet filter params
    category = request.args.get("category")
    format_filter = request.args.get("format")
    genre_filter = request.args.get("genre")
    collection_status = request.args.get("collection_status")

    try:
        # Build base item query for scope + cross-facet filtering
        base_item_q = (
            db.session.query(Item.id)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
        )

        if scope == "user":
            base_item_q = base_item_q.filter(Item.owner_id == user_id)

        if category:
            base_item_q = base_item_q.filter(Expression.content_type == category)
        if format_filter:
            base_item_q = base_item_q.filter(Manifestation.meta["format"].as_string() == format_filter)
        if genre_filter:
            base_item_q = base_item_q.filter(
                db.or_(
                    Work.meta["genres"].as_string().contains(genre_filter),
                    Work.meta["genre"].as_string().contains(genre_filter),
                )
            )
        if collection_status:
            base_item_q = base_item_q.filter(Item.collection_status == collection_status)

        item_ids_subq = base_item_q.subquery()

        # 1. Tags
        tags_query = (
            db.session.query(Tag.name)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .filter(ItemTag.item_id.in_(db.session.query(item_ids_subq.c.id)))
            .distinct()
            .all()
        )

        # 2. Collections
        if scope == "user":
            collections_query = db.session.query(UserCollection.name).filter(UserCollection.owner_id == user_id).distinct().all()
        else:
            collections_query = db.session.query(UserCollection.name).distinct().all()

        # 3. Publishers
        publishers_query = (
            db.session.query(Manifestation.publisher)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .filter(
                Manifestation.publisher.isnot(None),
                Manifestation.publisher != "",
                Item.id.in_(db.session.query(item_ids_subq.c.id)),
            )
            .distinct()
            .all()
        )

        # 4. Genres (from Work.meta)
        work_ids_query = (
            db.session.query(Work.id)
            .join(Expression, Expression.work_id == Work.id)
            .join(Manifestation, Manifestation.expression_id == Expression.id)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .filter(Item.id.in_(db.session.query(item_ids_subq.c.id)))
            .distinct()
            .all()
        )
        w_ids = [r[0] for r in work_ids_query]

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
