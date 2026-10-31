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
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select

from app.core.iri import canonical_actor_iri, get_federation_base_url
from app.core.notifications import create_notification
from app.db import db
from app.db.auth import User, UserFriendship
from app.db.federation import (
    FederationActivity,
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)

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

    # Also include accepted and pending federated followers/actors
    fed_stmt = (
        select(FederationFollower, FederationActor)
        .join(FederationActor, FederationFollower.remote_actor_id == FederationActor.id)
        .where(FederationFollower.local_user_id == u_uuid)
    )
    fed_results = db.session.execute(fed_stmt).all()

    # Pre-fetch outbound and inbound Follow activities for accurate directional segregation
    outbound_acts = (
        db.session.execute(
            select(FederationActivity).where(
                FederationActivity.direction == "outbound",
                FederationActivity.activity_type == "Follow",
                or_(
                    FederationActivity.actor_uri.ilike(f"%{u_uuid}%"),
                    FederationActivity.actor_uri == canonical_actor_iri(u_uuid),
                ),
            )
        )
        .scalars()
        .all()
    )

    outbound_by_target: dict[str, datetime] = {}
    for o_act in outbound_acts:
        if not o_act.created_at:
            continue
        if o_act.target_uri:
            prev = outbound_by_target.get(o_act.target_uri)
            if not prev or o_act.created_at > prev:
                outbound_by_target[o_act.target_uri] = o_act.created_at
        if isinstance(o_act.object_json, dict):
            obj = o_act.object_json.get("object")
            if isinstance(obj, str):
                prev = outbound_by_target.get(obj)
                if not prev or o_act.created_at > prev:
                    outbound_by_target[obj] = o_act.created_at

    pending_actor_uris = [act.actor_uri for fol, act in fed_results if fol.status == FollowStatus.PENDING and act.actor_uri]
    inbound_by_actor: dict[str, datetime] = {}
    if pending_actor_uris:
        local_actor_iri = canonical_actor_iri(u_uuid)
        inbound_acts = (
            db.session.execute(
                select(FederationActivity).where(
                    FederationActivity.direction == "inbound",
                    FederationActivity.activity_type == "Follow",
                    FederationActivity.actor_uri.in_(pending_actor_uris),
                )
            )
            .scalars()
            .all()
        )
        for i_act in inbound_acts:
            if not i_act.actor_uri or not i_act.created_at:
                continue
            target_match = False
            if i_act.target_uri and (i_act.target_uri == local_actor_iri or str(u_uuid) in i_act.target_uri):
                target_match = True
            elif isinstance(i_act.object_json, dict):
                obj = i_act.object_json.get("object")
                if isinstance(obj, str) and (obj == local_actor_iri or str(u_uuid) in obj):
                    target_match = True
            if target_match:
                prev = inbound_by_actor.get(i_act.actor_uri)
                if not prev or i_act.created_at > prev:
                    inbound_by_actor[i_act.actor_uri] = i_act.created_at

    for fol, act in fed_results:
        fed_data = {
            "friendship_id": f"fed:{fol.id}",
            "user_id": str(fol.remote_actor_id),
            "username": act.username or act.actor_uri,
            "display_name": act.display_name or act.username,
            "avatar_url": None,
            "status": fol.status,
            "created_at": fol.created_at.isoformat() if fol.created_at else None,
            "is_federated": True,
            "actor_uri": act.actor_uri,
        }
        if fol.status == FollowStatus.ACCEPTED:
            accepted.append(fed_data)
        elif fol.status == FollowStatus.PENDING:
            latest_out = None
            if act.actor_uri and act.actor_uri in outbound_by_target:
                latest_out = outbound_by_target[act.actor_uri]
            if act.inbox_url and act.inbox_url in outbound_by_target:
                inbox_time = outbound_by_target[act.inbox_url]
                if not latest_out or inbox_time > latest_out:
                    latest_out = inbox_time

            latest_in = inbound_by_actor.get(act.actor_uri) if act.actor_uri else None

            if latest_out and (not latest_in or latest_out > latest_in):
                outgoing.append(fed_data)
            else:
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
                "friendship_id": str(new_friendship.id),
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
        handle_parts = clean_id.lstrip("@").rsplit("@", 1)
        if len(handle_parts) == 2:
            target_username, target_domain = handle_parts[0], handle_parts[1]
        else:
            target_username, target_domain = handle_parts[0], None

        if target_domain:
            from app.core.federation_discovery import clean_instance_domain

            target_domain = clean_instance_domain(target_domain)
            inst = db.session.execute(select(FederationInstance).where(FederationInstance.domain == target_domain)).scalars().first()
            if inst and inst.trust_level == TrustLevel.BLOCKED:
                return None, f"Cannot connect with user from blocked instance {target_domain}", 403

        actor = None
        if target_domain:
            actor = (
                db.session.execute(
                    select(FederationActor).where(
                        or_(
                            FederationActor.username == target_username,
                            FederationActor.actor_uri.ilike(f"%/{target_username}"),
                        ),
                        FederationActor.actor_uri.ilike(f"%{target_domain}%"),
                    )
                )
                .scalars()
                .first()
            )

        if not actor:
            actor = (
                db.session.execute(
                    select(FederationActor).where(
                        or_(
                            FederationActor.actor_uri == clean_id,
                            FederationActor.username == target_username,
                        )
                    )
                )
                .scalars()
                .first()
            )

        # If not cached locally, try webfinger / remote actor lookup
        if not actor and target_domain:
            try:
                from app.core.federation_handlers import _get_or_create_actor
                from app.utils.http_client import safe_get

                scheme = (
                    "http"
                    if ("localhost" in target_domain or "127.0.0.1" in target_domain or target_domain.startswith("peer-web"))
                    else "https"
                )
                wf_url = f"{scheme}://{target_domain}/.well-known/webfinger?resource=acct:{target_username}@{target_domain}"
                wf_resp = safe_get(wf_url, headers={"Accept": "application/jrd+json, application/json"}, timeout=5.0)
                if wf_resp.status_code == 200:
                    for link in wf_resp.json().get("links", []):
                        if link.get("rel") == "self":
                            remote_actor_uri = link.get("href")
                            if remote_actor_uri:
                                actor = _get_or_create_actor(remote_actor_uri)
                                break
            except Exception as exc:
                logger.warning("Failed WebFinger lookup for %s: %s", clean_id, exc)

        # Fallback for email-like handles across registered non-blocked peer instances
        if not actor:
            from app.core.federation_handlers import _get_or_create_actor
            from app.utils.http_client import safe_get

            registered_instances = (
                db.session.execute(
                    select(FederationInstance)
                    .where(FederationInstance.trust_level != TrustLevel.BLOCKED)
                    .order_by(FederationInstance.last_seen_at.desc().nullslast())
                    .limit(5)
                )
                .scalars()
                .all()
            )
            for reg_inst in registered_instances:
                if reg_inst.domain == target_domain:
                    continue
                try:
                    scheme = (
                        "http"
                        if ("localhost" in reg_inst.domain or "127.0.0.1" in reg_inst.domain or reg_inst.domain.startswith("peer-web"))
                        else "https"
                    )
                    handle_user = clean_id.lstrip("@")
                    if "@" in handle_user:
                        handle_user = handle_user.split("@", 1)[0]
                    wf_url = f"{scheme}://{reg_inst.domain}/.well-known/webfinger?resource=acct:{handle_user}@{reg_inst.domain}"
                    wf_resp = safe_get(wf_url, headers={"Accept": "application/jrd+json, application/json"}, timeout=5.0)
                    if wf_resp.status_code == 200:
                        for link in wf_resp.json().get("links", []):
                            if link.get("rel") == "self":
                                remote_actor_uri = link.get("href")
                                if remote_actor_uri:
                                    actor = _get_or_create_actor(remote_actor_uri)
                                    break
                    if actor:
                        break
                except Exception:
                    pass

        if actor:
            if actor.instance and actor.instance.trust_level == TrustLevel.BLOCKED:
                return None, f"Cannot connect with user from blocked instance {actor.instance.domain}", 403
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
                if existing_fol.status == FollowStatus.ACCEPTED:
                    return None, "Already friends with this federated user", 409
                if existing_fol.status == FollowStatus.PENDING:
                    return None, "Friend request already sent", 409
                existing_fol.status = FollowStatus.PENDING
                db.session.commit()
                try:
                    from app.core.federation_dispatch import dispatch_follow

                    dispatch_follow(requester, actor)
                except Exception as exc:
                    logger.warning("Failed dispatching follow activity for existing follower: %s", exc)
                res_dict = existing_fol.to_dict()
                res_dict["id"] = f"fed:{existing_fol.id}"
                return res_dict, None, 200

            # Ensure requester has opted-in federated profile so remote instance can verify HTTP signature
            req_consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == req_uuid)).scalars().first()
            if not req_consent:
                req_consent = FederationConsent(
                    user_id=req_uuid,
                    federated_profile=True,
                    federated_collection=False,
                )
                db.session.add(req_consent)
            elif not req_consent.federated_profile:
                req_consent.federated_profile = True
                req_consent.updated_at = datetime.now(UTC)

            if not requester.federation_public_key:
                from app.core import federation_keys

                try:
                    base_url = get_federation_base_url()
                    existing_pub = federation_keys.get_actor_public_key(str(requester.id))
                    if existing_pub:
                        public_key_pem = existing_pub
                    else:
                        _, public_key_pem = federation_keys.generate_actor_keypair(str(requester.id))
                    canonical_uri = canonical_actor_iri(requester.id, base_url)
                    requester.federation_public_key = public_key_pem
                    requester.federation_key_id = f"{canonical_uri}#main-key"
                except Exception as exc:
                    logger.warning("Failed auto-generating actor keypair for outbound friend request: %s", exc)

            fol = FederationFollower(
                local_user_id=req_uuid,
                remote_actor_id=actor.id,
                status=FollowStatus.PENDING,
            )
            db.session.add(fol)
            db.session.commit()

            # Dispatch outbound Follow activity via Celery / federation dispatcher
            try:
                from app.core.federation_dispatch import dispatch_follow

                dispatch_follow(requester, actor)
            except Exception as exc:
                logger.warning("Failed dispatching outbound Follow for %s: %s", actor.actor_uri, exc)

            res_dict = fol.to_dict()
            res_dict["id"] = f"fed:{fol.id}"
            return res_dict, None, 201

    return None, f"User '{clean_id}' not found", 404


def respond_friend_request(
    user_id: uuid.UUID | str,
    friendship_id: int | str,
    action: str,
) -> tuple[dict[str, Any] | None, str | None, int]:
    """Accept or reject an incoming friend request.

    Args:
        user_id: UUID of recipient (must match addressee_id).
        friendship_id: Primary key of UserFriendship or prefixed federated ID (e.g. 'fed:123').
        action: 'accept' or 'reject'.

    Returns:
        (result_data, error_message, http_code)
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return None, "Invalid user ID", 400

    str_fid = str(friendship_id)
    if str_fid.startswith("fed:"):
        try:
            fed_fol_id = int(str_fid.split(":", 1)[1])
        except ValueError:
            return None, "Invalid federated friendship ID", 400

        fol = db.session.get(FederationFollower, fed_fol_id)
        if not fol or fol.local_user_id != u_uuid:
            return None, "Federated friend request not found", 404

        remote_act = db.session.get(FederationActor, fol.remote_actor_id)

        # Disallow caller responding (accept/reject) to an outbound follow request they initiated,
        # unless remote actor subsequently sent an inbound follow to the caller.
        if remote_act:
            outbound_acts = (
                db.session.execute(
                    select(FederationActivity).where(
                        FederationActivity.direction == "outbound",
                        FederationActivity.activity_type == "Follow",
                        or_(
                            FederationActivity.actor_uri.ilike(f"%{u_uuid}%"),
                            FederationActivity.actor_uri == canonical_actor_iri(u_uuid),
                        ),
                    )
                )
                .scalars()
                .all()
            )
            matching_outbound = []
            for o_act in outbound_acts:
                is_outbound_match = False
                if o_act.target_uri and (o_act.target_uri == remote_act.inbox_url or o_act.target_uri == remote_act.actor_uri):
                    is_outbound_match = True
                elif isinstance(o_act.object_json, dict) and o_act.object_json.get("object") == remote_act.actor_uri:
                    is_outbound_match = True
                if is_outbound_match:
                    matching_outbound.append(o_act)

            if matching_outbound:
                latest_outbound_time = max((o.created_at for o in matching_outbound if o.created_at), default=None)
                base_url = get_federation_base_url()
                local_actor_iri = canonical_actor_iri(u_uuid, base_url)
                inbound_candidates = (
                    db.session.execute(
                        select(FederationActivity)
                        .where(
                            FederationActivity.direction == "inbound",
                            FederationActivity.activity_type == "Follow",
                            FederationActivity.actor_uri == remote_act.actor_uri,
                        )
                        .order_by(FederationActivity.created_at.desc())
                    )
                    .scalars()
                    .all()
                )
                latest_inbound = None
                for candidate in inbound_candidates:
                    if candidate.target_uri and (candidate.target_uri == local_actor_iri or str(u_uuid) in candidate.target_uri):
                        latest_inbound = candidate
                        break
                    if isinstance(candidate.object_json, dict):
                        obj = candidate.object_json.get("object")
                        if isinstance(obj, str) and (obj == local_actor_iri or str(u_uuid) in obj):
                            latest_inbound = candidate
                            break

                latest_inbound_time = latest_inbound.created_at if latest_inbound else None
                if latest_outbound_time and (not latest_inbound_time or latest_outbound_time > latest_inbound_time):
                    return None, "Cannot respond to an outgoing request you initiated; use cancel instead", 400

        if action == "accept":
            fol.status = FollowStatus.ACCEPTED
            db.session.commit()

            # Send ActivityPub Accept
            try:
                from app.core.federation_dispatch import dispatch_accept_follow

                user = db.session.get(User, u_uuid)
                if user and remote_act:
                    base_url = get_federation_base_url()
                    local_actor_iri = canonical_actor_iri(user.id, base_url)
                    dummy_follow = {
                        "type": "Follow",
                        "actor": remote_act.actor_uri,
                        "object": local_actor_iri,
                    }
                    dispatch_accept_follow(user, remote_act, dummy_follow)
            except Exception as exc:
                logger.warning("Failed dispatching Accept for federated follow: %s", exc)

            res = fol.to_dict()
            res["id"] = f"fed:{fol.id}"
            return res, None, 200
        elif action == "reject":
            # Send ActivityPub Reject
            try:
                from app.core.federation_dispatch import dispatch_reject_follow

                user = db.session.get(User, u_uuid)
                if user and remote_act:
                    base_url = get_federation_base_url()
                    local_actor_iri = canonical_actor_iri(user.id, base_url)
                    dummy_follow = {
                        "type": "Follow",
                        "actor": remote_act.actor_uri,
                        "object": local_actor_iri,
                    }
                    dispatch_reject_follow(user, remote_act, dummy_follow)
            except Exception as exc:
                logger.warning("Failed dispatching Reject for federated follow: %s", exc)

            db.session.delete(fol)
            db.session.commit()
            return {"id": str_fid, "status": "rejected"}, None, 200
        else:
            return None, "Invalid action. Must be 'accept' or 'reject'", 400

    try:
        numeric_fid = int(str_fid)
    except ValueError:
        return None, "Invalid friendship ID", 400

    friendship = db.session.get(UserFriendship, numeric_fid)
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
        return {"id": numeric_fid, "status": "rejected"}, None, 200
    else:
        return None, "Invalid action. Must be 'accept' or 'reject'", 400


def remove_friend(
    user_id: uuid.UUID | str,
    friendship_id: int | str,
) -> tuple[bool, str | None, int]:
    """Remove an existing friendship or cancel a request.

    Args:
        user_id: UUID of caller.
        friendship_id: Primary key of UserFriendship or prefixed federated ID (e.g. 'fed:123').

    Returns:
        (success, error_message, http_code)
    """
    try:
        u_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except ValueError:
        return False, "Invalid user ID", 400

    str_fid = str(friendship_id)
    if str_fid.startswith("fed:"):
        try:
            fed_fol_id = int(str_fid.split(":", 1)[1])
        except ValueError:
            return False, "Invalid federated friendship ID", 400

        fol = db.session.get(FederationFollower, fed_fol_id)
        if not fol or fol.local_user_id != u_uuid:
            return False, "Federated friendship not found", 404

        remote_act = db.session.get(FederationActor, fol.remote_actor_id)
        user = db.session.get(User, u_uuid)
        db.session.delete(fol)
        db.session.commit()

        if user and remote_act and remote_act.inbox_url:
            try:
                from app.core.federation_dispatch import dispatch_undo_follow

                dispatch_undo_follow(user, remote_act)
            except Exception as exc:
                logger.warning("Failed dispatching Undo for federated follow removal: %s", exc)

        return True, None, 200

    try:
        numeric_fid = int(str_fid)
    except ValueError:
        return False, "Invalid friendship ID", 400

    friendship = db.session.get(UserFriendship, numeric_fid)
    if not friendship:
        return False, "Friendship not found", 404

    if friendship.requester_id != u_uuid and friendship.addressee_id != u_uuid:
        return False, "Forbidden", 403

    db.session.delete(friendship)
    db.session.commit()
    return True, None, 200
