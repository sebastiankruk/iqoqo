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
"""Public profile and user inventory endpoints for iqoqo v0.7.0.

Handles public profile retrieval and "check if I have it" inventory search.
"""

from flask import jsonify, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.public_rdf import public_bp
from app.db.models import Item, Manifestation, User, Work, db


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
