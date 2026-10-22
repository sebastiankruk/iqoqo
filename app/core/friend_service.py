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
"""Friendship and mutual contact management service.

Handles local user friendships and federated contact relationships,
authorizing access to 'friends_only' visibility tiers across the catalog.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import and_, or_, select

from app.core.notifications import create_notification
from app.db import db
from app.db.auth import User, UserFriendship
from app.db.federation import FederationActor, FederationFollower, FollowStatus

logger = logging.getLogger(__name__)


def is_friend_of(
    viewer_user_id: uuid.UUID | str | None,
    owner_user_id: uuid.UUID | str,
    remote_actor_id: int | str | None = None,
) -> bool:
    """Determine whether a viewer is an accepted friend of an entity owner.

    Args:
        viewer_user_id: UUID or string ID of the viewing local user, or None if anonymous/remote.
        owner_user_id: UUID or string ID of the resource owner.
        remote_actor_id: Optional ID of remote ActivityPub actor.

    Returns:
        True if the viewer is identical to owner or has an accepted friendship.
    """
    if not owner_user_id:
        return False

    # Owner always sees own items
    if viewer_user_id and str(viewer_user_id) == str(owner_user_id):
        return True

    try:
        owner_uuid = uuid.UUID(str(owner_user_id)) if not isinstance(owner_user_id, uuid.UUID) else owner_user_id
    except ValueError:
        return False

    # Check local friendship
    if viewer_user_id:
        try:
            viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
            stmt = select(UserFriendship.id).where(
                UserFriendship.status == "accepted",
                or_(
                    and_(UserFriendship.requester_id == viewer_uuid, UserFriendship.addressee_id == owner_uuid),
                    and_(UserFriendship.requester_id == owner_uuid, UserFriendship.addressee_id == viewer_uuid),
                ),
            )
            if db.session.execute(stmt).scalar() is not None:
                return True
        except ValueError:
            pass

    # Check federated follow / friend relationship
    if remote_actor_id is not None:
        try:
            actor_id_int = int(remote_actor_id)
            stmt = select(FederationFollower.id).where(
                FederationFollower.local_user_id == owner_uuid,
                FederationFollower.remote_actor_id == actor_id_int,
                FederationFollower.status == FollowStatus.ACCEPTED,
            )
            if db.session.execute(stmt).scalar() is not None:
                return True
        except (ValueError, TypeError):
            pass

    return False


def get_friend_user_ids(user_id: uuid.UUID | str) -> set[uuid.UUID]:
    """Retrieve all local user UUIDs who share an accepted friendship with user_id.

    Args:
        user_id: Target user UUID.

    Returns:
        Set of friend UUIDs.
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return set()

    stmt = select(UserFriendship).where(
        UserFriendship.status == "accepted",
        or_(UserFriendship.requester_id == u_uuid, UserFriendship.addressee_id == u_uuid),
    )
    rows = db.session.execute(stmt).scalars().all()
    friends: set[uuid.UUID] = set()
    for row in rows:
        if row.requester_id == u_uuid:
            friends.add(row.addressee_id)
        else:
            friends.add(row.requester_id)
    return friends


def list_friends(user_id: uuid.UUID | str) -> dict[str, list[dict[str, Any]]]:
    """Return lists of accepted friends, incoming requests, and outgoing requests.

    Args:
        user_id: Target user UUID.

    Returns:
        Dictionary with 'accepted', 'incoming', and 'outgoing' lists.
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return {"accepted": [], "incoming": [], "outgoing": []}

    stmt = select(UserFriendship).where(or_(UserFriendship.requester_id == u_uuid, UserFriendship.addressee_id == u_uuid))
    friendships = db.session.execute(stmt).scalars().all()

    accepted = []
    incoming = []
    outgoing = []

    for f in friendships:
        is_requester = f.requester_id == u_uuid
        other_user = f.addressee if is_requester else f.requester
        if not other_user:
            continue

        item_data = {
            "friendship_id": f.id,
            "user_id": str(other_user.id),
            "username": other_user.public_username or other_user.email,
            "display_name": other_user.display_name or other_user.public_username,
            "avatar_url": other_user.avatar_url,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "is_federated": False,
        }

        if f.status == "accepted":
            accepted.append(item_data)
        elif f.status == "pending":
            if is_requester:
                outgoing.append(item_data)
            else:
                incoming.append(item_data)

    # Also include accepted federated followers/actors
    fed_stmt = (
        select(FederationFollower, FederationActor)
        .join(FederationActor, FederationFollower.remote_actor_id == FederationActor.id)
        .where(FederationFollower.local_user_id == u_uuid)
    )
    fed_results = db.session.execute(fed_stmt).all()
    for fol, act in fed_results:
        fed_data = {
            "friendship_id": fol.id,
            "user_id": str(fol.remote_actor_id),
            "username": act.preferred_username or act.uri,
            "display_name": act.name or act.preferred_username,
            "avatar_url": None,
            "status": fol.status,
            "created_at": fol.created_at.isoformat() if fol.created_at else None,
            "is_federated": True,
            "actor_uri": act.uri,
        }
        if fol.status == FollowStatus.ACCEPTED:
            accepted.append(fed_data)
        elif fol.status == FollowStatus.PENDING:
            incoming.append(fed_data)

    return {"accepted": accepted, "incoming": incoming, "outgoing": outgoing}


def send_friend_request(
    requester_id: uuid.UUID | str,
    target_identifier: str,
) -> tuple[dict[str, Any] | None, str | None, int]:
    """Initiate a friend request to a local user or federated actor.

    Args:
        requester_id: UUID of requester.
        target_identifier: Username, email, or @user@domain handle.

    Returns:
        (result_data, error_message, http_code)
    """
    clean_id = (target_identifier or "").strip()
    if not clean_id:
        return None, "Target user identifier is required", 400

    try:
        req_uuid = uuid.UUID(str(requester_id)) if not isinstance(requester_id, uuid.UUID) else requester_id
    except ValueError:
        return None, "Invalid requester ID", 400

    requester = db.session.get(User, req_uuid)
    if not requester:
        return None, "Requester not found", 404

    # Check if target is a local user by public_username or email
    target_user = (
        db.session.execute(
            select(User).where(
                or_(
                    User.public_username == clean_id,
                    User.email == clean_id,
                )
            )
        )
        .scalars()
        .first()
    )

    if target_user:
        if target_user.id == req_uuid:
            return None, "Cannot friend yourself", 400

        # Check existing friendship
        existing = (
            db.session.execute(
                select(UserFriendship).where(
                    or_(
                        and_(UserFriendship.requester_id == req_uuid, UserFriendship.addressee_id == target_user.id),
                        and_(UserFriendship.requester_id == target_user.id, UserFriendship.addressee_id == req_uuid),
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing:
            if existing.status == "accepted":
                return None, "Already friends with this user", 409
            if existing.status == "pending":
                if existing.requester_id == req_uuid:
                    return None, "Friend request already sent", 409
                # If target already sent a request, auto-accept it!
                existing.status = "accepted"
                db.session.commit()
                create_notification(
                    user_id=target_user.id,
                    notification_type="friend_accepted",
                    payload={
                        "friend_id": str(requester.id),
                        "username": requester.public_username or requester.email,
                        "message": f"{requester.public_username or requester.email} accepted your friend request",
                        "target_iri": "/profile?tab=accepted#friends",
                    },
                    target_iri="/profile?tab=accepted#friends",
                )
                return existing.to_dict(), None, 200

        new_friendship = UserFriendship(
            requester_id=req_uuid,
            addressee_id=target_user.id,
            status="pending",
        )
        db.session.add(new_friendship)
        db.session.flush()

        create_notification(
            user_id=target_user.id,
            notification_type="friend_request",
            payload={
                "requester_id": str(requester.id),
                "username": requester.public_username or requester.email,
                "message": f"New friend request from {requester.public_username or requester.email}",
                "target_iri": "/profile?tab=incoming#friends",
            },
            target_iri="/profile?tab=incoming#friends",
        )
        db.session.commit()
        return new_friendship.to_dict(), None, 201

    # Check if handle represents a federated actor (@user@domain)
    if "@" in clean_id:
        actor = (
            db.session.execute(
                select(FederationActor).where(
                    or_(
                        FederationActor.uri == clean_id,
                        FederationActor.preferred_username == clean_id.lstrip("@").split("@")[0],
                    )
                )
            )
            .scalars()
            .first()
        )
        if actor:
            existing_fol = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == req_uuid,
                        FederationFollower.remote_actor_id == actor.id,
                    )
                )
                .scalars()
                .first()
            )
            if existing_fol:
                return existing_fol.to_dict(), None, 200
            fol = FederationFollower(
                local_user_id=req_uuid,
                remote_actor_id=actor.id,
                status=FollowStatus.ACCEPTED,
            )
            db.session.add(fol)
            db.session.commit()
            return fol.to_dict(), None, 201

    return None, f"User '{clean_id}' not found", 404


def respond_friend_request(
    user_id: uuid.UUID | str,
    friendship_id: int,
    action: str,
) -> tuple[dict[str, Any] | None, str | None, int]:
    """Accept or reject an incoming friend request.

    Args:
        user_id: UUID of recipient (must match addressee_id).
        friendship_id: Primary key of UserFriendship.
        action: 'accept' or 'reject'.

    Returns:
        (result_data, error_message, http_code)
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return None, "Invalid user ID", 400

    friendship = db.session.get(UserFriendship, friendship_id)
    if not friendship:
        return None, "Friend request not found", 404

    if friendship.addressee_id != u_uuid:
        return None, "Forbidden: you can only respond to incoming requests addressed to you", 403

    if action == "accept":
        friendship.status = "accepted"
        db.session.commit()
        user = db.session.get(User, u_uuid)
        create_notification(
            user_id=friendship.requester_id,
            notification_type="friend_accepted",
            payload={
                "friend_id": str(u_uuid),
                "username": user.public_username if user else "Friend",
                "message": f"{user.public_username if user else 'A user'} accepted your friend request",
                "target_iri": "/profile?tab=accepted#friends",
            },
            target_iri="/profile?tab=accepted#friends",
        )
        return friendship.to_dict(), None, 200
    elif action == "reject":
        friendship.status = "rejected"
        db.session.delete(friendship)
        db.session.commit()
        return {"id": friendship_id, "status": "rejected"}, None, 200
    else:
        return None, "Invalid action. Must be 'accept' or 'reject'", 400


def remove_friend(
    user_id: uuid.UUID | str,
    friendship_id: int,
) -> tuple[bool, str | None, int]:
    """Remove an existing friendship or cancel a request.

    Args:
        user_id: UUID of caller.
        friendship_id: Primary key of UserFriendship.

    Returns:
        (success, error_message, http_code)
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return False, "Invalid user ID", 400

    friendship = db.session.get(UserFriendship, friendship_id)
    if not friendship:
        return False, "Friendship not found", 404

    if friendship.requester_id != u_uuid and friendship.addressee_id != u_uuid:
        return False, "Forbidden", 403

    db.session.delete(friendship)
    db.session.commit()
    return True, None, 200
