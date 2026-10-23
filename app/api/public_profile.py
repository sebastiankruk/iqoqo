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

from flask import g, jsonify, request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.decorators import optional_auth
from app.api.public_rdf import public_bp
from app.core.limiter import limiter
from app.db.models import Item, Manifestation, User, Work, db


@public_bp.route("/u/<string:username>", methods=["GET"])
@optional_auth
@limiter.limit("60 per minute")
def get_public_profile(username: str):
    """Retrieve a user's public profile stats and basic info."""
    user = db.session.execute(select(User).where(func.lower(User.public_username) == username.lower())).scalar_one_or_none()

    if not user:
        return jsonify({"error": "Public profile not found or user has disabled public sharing."}), 404

    viewer_id = getattr(g, "user_id", None)
    is_owner = bool(viewer_id and str(viewer_id) == str(user.id))

    from app.core.friend_service import is_friend_of

    is_friend = is_friend_of(viewer_id, user.id) if viewer_id else False

    if user.visibility == "private" and not is_owner:
        return jsonify({"error": "Public profile not found or user has disabled public sharing."}), 404
    if user.visibility == "friends_only" and not (is_owner or is_friend):
        return jsonify({"error": "Public profile not found or user has disabled public sharing."}), 404

    if is_owner or is_friend:
        count_stmt = select(func.count(Item.id)).where(  # pylint: disable=not-callable
            Item.owner_id == user.id,
            or_(Item.is_hidden.is_(False), Item.visibility.in_(["public", "friends_only", "shared"])),
        )
    else:
        count_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, Item.is_hidden.is_(False))  # pylint: disable=not-callable

    item_count = db.session.execute(count_stmt).scalar() or 0

    return jsonify(
        {
            "success": True,
            "data": {
                "username": user.public_username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "bio": user.bio,
                "public_item_count": item_count,
                "is_friend": is_friend,
            },
        }
    )


@public_bp.route("/u/<string:username>/check", methods=["POST"])
@optional_auth
@limiter.limit("30 per minute")
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

    friend_items = []
    # If include_friends is requested, allow if anonymous or owner/friend (unauthenticated public requests default to public friends)
    if data.get("include_friends"):
        from app.core.friend_service import get_friend_user_ids

        local_friend_ids = list(get_friend_user_ids(user.id))
        if local_friend_ids:
            local_friend_stmt = (
                select(Item)
                .join(Manifestation)
                .join(Manifestation.expression)
                .join(Work)
                .where(
                    Item.owner_id.in_(local_friend_ids),
                    or_(Item.is_hidden.is_(False), Item.visibility.in_(["public", "friends_only", "shared"])),
                    or_(
                        Work.title.ilike(f"%{query_term}%"),
                        Manifestation.isbn13 == query_term,
                        Manifestation.upc == query_term,
                        db.cast(Manifestation.meta, db.String).ilike(f"%{query_term}%"),
                    ),
                )
                .limit(5)
            )
            local_friend_items = db.session.execute(local_friend_stmt.options(selectinload(Item.manifestation))).scalars().all()
            for lfi in local_friend_items:
                owner_obj = db.session.get(User, lfi.owner_id)
                handle = (owner_obj.public_username or owner_obj.email) if owner_obj else "friend"
                friend_items.append(
                    {
                        "type": "friend_item",
                        "id": lfi.id,
                        "title": lfi.manifestation.title if lfi.manifestation else "",
                        "status": lfi.status,
                        "collection_status": lfi.collection_status,
                        "cover_url": lfi.manifestation.cover_url if lfi.manifestation else None,
                        "owner_handle": f"@{handle}",
                        "owner_actor_uri": None,
                    }
                )

        from app.core.federation_client import FederationClient
        from app.db.federation import FederationActor, FederationFollower, FollowStatus

        friend_stmt = (
            select(FederationActor)
            .join(FederationFollower, FederationFollower.remote_actor_id == FederationActor.id)
            .where(
                FederationFollower.local_user_id == user.id,
                FederationFollower.status == FollowStatus.ACCEPTED,
            )
            .limit(5)
        )
        friend_actors = db.session.execute(friend_stmt).scalars().all()
        client = FederationClient()
        for friend in friend_actors:
            try:
                col = client.fetch_actor_collections(friend.actor_uri)
                if col and isinstance(col, dict):
                    items_list = col.get("orderedItems") or col.get("items") or []
                    for it in items_list:
                        if isinstance(it, dict):
                            title = it.get("name") or it.get("title") or ""
                            if query_term.lower() in title.lower():
                                domain = friend.instance.domain if friend.instance else "remote"
                                handle = f"@{friend.username}@{domain}" if friend.username else friend.actor_uri
                                friend_items.append(
                                    {
                                        "type": "friend_item",
                                        "id": it.get("id") or 0,
                                        "title": title,
                                        "status": it.get("status", "available"),
                                        "collection_status": it.get("collection_status", "available"),
                                        "cover_url": it.get("image") or it.get("cover_url"),
                                        "owner_handle": handle,
                                        "owner_actor_uri": friend.actor_uri,
                                    }
                                )
            except Exception:
                pass

    if items or friend_items:
        results = [
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
        ]
        results.extend(friend_items)
        return jsonify(
            {
                "success": True,
                "data": results,
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
