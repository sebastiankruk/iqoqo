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
"""Public API endpoints for iqoqo v0.7.0.
Handles public profile retrieval, public item grids, and "check if I have it" functionality.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.db.models import Expression, Item, Manifestation, SharedCollection, User, Work, db

public_bp = Blueprint("public", __name__, url_prefix="/public")


@public_bp.route("/u/<string:username>", methods=["GET"])
def get_public_profile(username: str):
    """Retrieve a user's public profile stats and basic info."""
    stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(stmt).scalar_one_or_none()

    if not user:
        return jsonify({"error": "Public profile not found or user has disabled public sharing."}), 404

    count_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, Item.is_hidden.is_(False))  # pylint: disable=not-callable
    item_count = db.session.execute(count_stmt).scalar()

    return jsonify(
        {
            "success": True,
            "data": {
                "username": user.public_username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "bio": user.bio,
                "public_item_count": item_count,
            },
        }
    )


@public_bp.route("/u/<string:username>/items", methods=["GET"])
def get_public_items(username: str):
    """Retrieve public items for a user."""
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 24, type=int), 100)

    stmt = (
        select(Item)
        .options(selectinload(Item.manifestation))
        .where(Item.owner_id == user.id, Item.is_hidden.is_(False))
        .order_by(Item.updated_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    items = db.session.execute(stmt).scalars().all()

    total_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, Item.is_hidden.is_(False))  # pylint: disable=not-callable
    total = db.session.execute(total_stmt).scalar()

    return jsonify(
        {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "manifestation_id": item.manifestation_id,
                        "status": item.status,
                        "collection_status": item.collection_status,
                        "title": item.manifestation.title,
                        "authors": item.manifestation.meta.get("authors", []) if item.manifestation.meta else [],
                        "cover_url": item.manifestation.cover_url
                        or (item.manifestation.meta.get("cover_url") if item.manifestation.meta else None),
                        "added_at": item.added_at.isoformat() if item.added_at else None,
                    }
                    for item in items
                ],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if total else 0,
            },
        }
    )


@public_bp.route("/share/<string:token>", methods=["GET"])
def get_shared_collection(token: str):
    """Retrieve items based on a specific SharedCollection token filters."""
    stmt = select(SharedCollection).where(SharedCollection.share_token == token)
    collection = db.session.execute(stmt).scalar_one_or_none()
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    user = db.session.get(User, collection.user_id)
    if not user:
        return jsonify({"error": "Author not found"}), 404

    query = select(Item).where(Item.owner_id == user.id, Item.is_hidden.is_(False))

    filters = collection.filters

    if "status" in filters:
        # The frontend sends 'status' which could map to either Item.status or Item.collection_status
        status_val = filters["status"]
        query = query.where(or_(Item.status == status_val, Item.collection_status == status_val))

    if "tags" in filters:
        # tags array maps to Expression.content_type
        # We need to join Expression if it's not already joined
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        tags_list = filters["tags"]
        if tags_list:
            query = query.where(Expression.content_type.in_(tags_list))

    if "query" in filters:
        search_query = filters["query"]
        if search_query:
            # Join Work and Manifestation if not joined
            if "tags" not in filters:
                query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
                query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
            query = query.outerjoin(Work, Expression.work_id == Work.id)

            query = query.where(
                or_(
                    Work.title.ilike(f"%{search_query}%"),
                    Manifestation.isbn13 == search_query,
                    Manifestation.upc == search_query,
                    db.cast(Work.meta, db.String).ilike(f"%{search_query}%"),
                    db.cast(Manifestation.meta, db.String).ilike(f"%{search_query}%"),
                )
            )

    items = db.session.execute(query.options(selectinload(Item.manifestation))).scalars().all()

    return jsonify(
        {
            "success": True,
            "data": {
                "collection_name": collection.name,
                "collection_description": collection.description,
                "author": user.public_username or user.display_name or "A user",
                "items": [
                    {
                        "id": item.id,
                        "manifestation_id": item.manifestation_id,
                        "status": item.status,
                        "collection_status": item.collection_status,
                        "title": item.manifestation.title,
                        "authors": item.manifestation.meta.get("authors", []) if item.manifestation.meta else [],
                        "cover_url": item.manifestation.cover_url
                        or (item.manifestation.meta.get("cover_url") if item.manifestation.meta else None),
                    }
                    for item in items
                ],
            },
        }
    )


@public_bp.route("/u/<string:username>/check", methods=["POST"])
def check_inventory(username: str):
    """
    Smart check if a user has a specific item.
    Returns Item if owned, otherwise Manifestation if exists in catalog.
    """
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    query_term = data.get("query", "").strip()
    if not query_term:
        return jsonify({"error": "Query parameter is required"}), 400

    # 1. Search for Item owned by user
    # Join Item -> Manifestation -> Expression -> Work
    item_stmt = (
        select(Item)
        .join(Manifestation)
        .join(Manifestation.expression)
        .join(Work)
        .where(
            Item.owner_id == user.id,
            Item.is_hidden.is_(False),
            or_(
                Work.title.ilike(f"%{query_term}%"),
                Manifestation.isbn13 == query_term,
                Manifestation.upc == query_term,
                db.cast(Manifestation.meta, db.String).ilike(f"%{query_term}%"),
            ),
        )
        .order_by(Work.title.asc())
    )
    items = db.session.execute(item_stmt.options(selectinload(Item.manifestation)).limit(5)).scalars().all()

    if items:
        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "type": "item",
                        "id": item.id,
                        "manifestation_id": item.manifestation_id,
                        "title": item.manifestation.title,
                        "status": item.status,
                        "collection_status": item.collection_status,
                        "cover_url": item.manifestation.cover_url,
                    }
                    for item in items
                ],
            }
        )

    # 2. If no item, search for Manifestation in catalog
    manifestation_stmt = (
        select(Manifestation)
        .join(Manifestation.expression)
        .join(Work)
        .where(
            or_(
                Work.title.ilike(f"%{query_term}%"),
                Manifestation.isbn13 == query_term,
                Manifestation.upc == query_term,
                db.cast(Manifestation.meta, db.String).ilike(f"%{query_term}%"),
            )
        )
        .order_by(Work.title.asc())
    )
    manifestations = db.session.execute(manifestation_stmt.limit(5)).scalars().all()

    if manifestations:
        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "type": "manifestation",
                        "id": m.id,
                        "title": m.title,
                        "publisher": m.publisher,
                        "cover_url": m.cover_url,
                    }
                    for m in manifestations
                ],
            }
        )

    return jsonify({"success": True, "data": []})
