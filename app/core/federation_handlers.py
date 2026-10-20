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
"""ActivityPub activity handlers for inbound activities."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config_service import ConfigService
from app.db import db
from app.db.auth import User
from app.db.federation import (
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)

logger = logging.getLogger(__name__)


def handle_activity(activity: dict[str, Any]) -> bool:
    """Route an inbound activity to the appropriate handler.

    Args:
        activity: The parsed ActivityStreams activity.

    Returns:
        True if handled successfully, False otherwise.
    """
    activity_type = activity.get("type", "")

    handlers = {
        "Follow": handle_follow,
        "Undo": handle_undo,
        "Accept": handle_accept,
        "Reject": handle_reject,
        "Create": handle_create,
        "Update": handle_update,
        "Delete": handle_delete,
        "Announce": handle_announce,
    }

    handler = handlers.get(activity_type)
    if not handler:
        logger.warning("Unhandled activity type: %s", activity_type)
        return False

    try:
        return handler(activity)
    except (ValueError, KeyError, TypeError, AttributeError, IntegrityError):
        logger.exception("Error handling %s activity", activity_type)
        db.session.rollback()
        return False


def _get_or_create_actor(actor_uri: str) -> FederationActor | None:
    """Get or create a FederationActor record for the given URI."""
    stmt = select(FederationActor).where(FederationActor.actor_uri == actor_uri)
    actor = db.session.execute(stmt).scalars().first()
    if actor:
        return actor

    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return None

    inst_stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(inst_stmt).scalars().first()
    if not instance:
        default_trust = ConfigService.get("FEDERATION_DEFAULT_TRUST", TrustLevel.UNTRUSTED)
        instance = FederationInstance(domain=domain, trust_level=str(default_trust))
        db.session.add(instance)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            instance = db.session.execute(inst_stmt).scalars().first()

    if not instance:
        return None

    actor = FederationActor(
        actor_uri=actor_uri,
        inbox_url=f"{actor_uri}/inbox",
        instance_id=instance.id,
        last_fetched_at=datetime.now(UTC),
    )
    db.session.add(actor)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        actor = db.session.execute(stmt).scalars().first()
    return actor


def _resolve_target_user(object_uri: str) -> User | None:
    """Resolve local User from target actor object URI or username."""
    if not object_uri:
        return None

    if "/actor/u/" in object_uri:
        uuid_str = object_uri.split("/actor/u/")[-1].strip("/").split("#")[0]
        try:
            target_uuid = uuid.UUID(uuid_str)
            return db.session.execute(select(User).where(User.id == target_uuid)).scalars().first()
        except (ValueError, TypeError):
            return None

    parts = object_uri.rstrip("/").split("/")
    username = parts[-1].split("#")[0] if parts else None
    if not username:
        return None

    user = db.session.execute(select(User).where(User.public_username == username)).scalars().first()
    if not user:
        try:
            target_uuid = uuid.UUID(username)
            user = db.session.execute(select(User).where(User.id == target_uuid)).scalars().first()
        except (ValueError, TypeError):
            user = None
    return user


def handle_follow(activity: dict[str, Any]) -> bool:
    """Handle a Follow activity — remote actor wants to follow local user."""
    actor_uri = activity.get("actor", "")
    object_uri = activity.get("object", "")

    if not actor_uri or not object_uri:
        return False

    user = _resolve_target_user(object_uri)
    if not user:
        logger.warning("Follow target user not found: %s", object_uri)
        return False

    # Check federation consent
    consent_stmt = select(FederationConsent).where(FederationConsent.user_id == user.id)
    consent = db.session.execute(consent_stmt).scalars().first()
    if not consent or not consent.federated_profile:
        logger.info("Follow rejected — user %s has no federation consent", user.id)
        return False

    # Check instance trust
    remote_actor = _get_or_create_actor(actor_uri)
    if not remote_actor:
        return False

    instance = remote_actor.instance
    if instance and instance.trust_level == TrustLevel.BLOCKED:
        logger.warning("Follow rejected from blocked instance %s", instance.domain)
        return False

    # Check existing relationship
    follower_stmt = select(FederationFollower).where(
        FederationFollower.local_user_id == user.id,
        FederationFollower.remote_actor_id == remote_actor.id,
    )
    existing = db.session.execute(follower_stmt).scalars().first()

    auto_accept = current_app.config.get("FEDERATION_AUTO_ACCEPT_FOLLOWS", True)
    if isinstance(auto_accept, str):
        auto_accept = auto_accept.lower() in {"true", "1", "yes"}

    should_accept = bool(auto_accept or (instance and instance.trust_level == TrustLevel.TRUSTED))
    follow_status = FollowStatus.ACCEPTED if should_accept else FollowStatus.PENDING

    if existing:
        existing.status = follow_status
    else:
        follower = FederationFollower(
            local_user_id=user.id,
            remote_actor_id=remote_actor.id,
            status=follow_status,
        )
        db.session.add(follower)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.execute(follower_stmt).scalars().first()
        if existing:
            existing.status = follow_status
            db.session.commit()

    if should_accept:
        _accept_follow(user, remote_actor, activity)

    return True


def _accept_follow(user: User, remote_actor: FederationActor, original_activity: dict[str, Any]) -> None:
    """Accept a follow request and queue Accept activity."""
    follower_stmt = select(FederationFollower).where(
        FederationFollower.local_user_id == user.id,
        FederationFollower.remote_actor_id == remote_actor.id,
    )
    follower = db.session.execute(follower_stmt).scalars().first()
    if follower:
        follower.status = FollowStatus.ACCEPTED
        db.session.commit()

    try:
        from app.core.federation_dispatch import dispatch_accept_follow

        dispatch_accept_follow(user, remote_actor, original_activity)
    except Exception as exc:
        logger.warning("Failed to dispatch accept follow: %s", exc)


def handle_undo(activity: dict[str, Any]) -> bool:
    """Handle an Undo activity — typically Undo(Follow)."""
    inner = activity.get("object", {})
    if isinstance(inner, str):
        return False

    inner_type = inner.get("type", "")
    if inner_type == "Follow":
        return _handle_undo_follow(activity, inner)

    logger.warning("Unhandled Undo sub-type: %s", inner_type)
    return False


def _handle_undo_follow(activity: dict[str, Any], follow_activity: dict[str, Any]) -> bool:
    """Remove a follow relationship."""
    actor_uri = activity.get("actor", "")
    object_uri = follow_activity.get("object", "")

    if not actor_uri or not object_uri:
        return False

    user = _resolve_target_user(object_uri)
    if not user:
        return False

    stmt = select(FederationActor).where(FederationActor.actor_uri == actor_uri)
    remote_actor = db.session.execute(stmt).scalars().first()
    if not remote_actor:
        return False

    follower_stmt = select(FederationFollower).where(
        FederationFollower.local_user_id == user.id,
        FederationFollower.remote_actor_id == remote_actor.id,
    )
    follower = db.session.execute(follower_stmt).scalars().first()

    if follower:
        db.session.delete(follower)
        db.session.commit()

    return True


def handle_accept(activity: dict[str, Any]) -> bool:
    """Handle Accept activity (response to our outbound Follow request)."""
    actor_uri = activity.get("actor", "")
    inner = activity.get("object", {})

    if isinstance(inner, dict) and inner.get("type") == "Follow":
        followed_uri = inner.get("object", "")  # Target being followed
        follower_actor_uri = inner.get("actor", "")  # Who initiated the follow
    else:
        logger.info("Received Accept without Follow inner object from %s", actor_uri)
        return True

    # Remote actor accepting our follow must match the object being followed
    if followed_uri != actor_uri:
        logger.warning("Accept spoofing attempt: actor %s accepted follow intended for %s", actor_uri, followed_uri)
        return False

    stmt = select(FederationActor).where(FederationActor.actor_uri == actor_uri)
    remote_actor = db.session.execute(stmt).scalars().first()
    if not remote_actor:
        return True

    user = _resolve_target_user(follower_actor_uri)
    if not user:
        return True

    # Update follower record if tracking relationship
    follower_stmt = select(FederationFollower).where(
        FederationFollower.local_user_id == user.id,
        FederationFollower.remote_actor_id == remote_actor.id,
    )
    follower = db.session.execute(follower_stmt).scalars().first()
    if follower:
        follower.status = FollowStatus.ACCEPTED
        db.session.commit()

    logger.info("Follow accepted by %s for local user %s", actor_uri, user.public_username)
    return True


def handle_reject(activity: dict[str, Any]) -> bool:
    """Handle Reject activity (response to our outbound Follow request)."""
    actor_uri = activity.get("actor", "")
    inner = activity.get("object", {})

    if isinstance(inner, dict) and inner.get("type") == "Follow":
        followed_uri = inner.get("object", "")
        follower_actor_uri = inner.get("actor", "")
    else:
        logger.info("Received Reject without Follow inner object from %s", actor_uri)
        return True

    if followed_uri != actor_uri:
        logger.warning("Reject spoofing attempt: actor %s rejected follow intended for %s", actor_uri, followed_uri)
        return False

    stmt = select(FederationActor).where(FederationActor.actor_uri == actor_uri)
    remote_actor = db.session.execute(stmt).scalars().first()
    if not remote_actor:
        return True

    user = _resolve_target_user(follower_actor_uri)
    if not user:
        return True

    follower_stmt = select(FederationFollower).where(
        FederationFollower.local_user_id == user.id,
        FederationFollower.remote_actor_id == remote_actor.id,
    )
    follower = db.session.execute(follower_stmt).scalars().first()
    if follower:
        follower.status = FollowStatus.REJECTED
        db.session.commit()

    logger.info("Follow rejected by %s for local user %s", actor_uri, user.public_username)
    return True


def handle_create(activity: dict[str, Any]) -> bool:
    """Handle Create activity — receive remote collection or metadata updates."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    if isinstance(obj, str):
        logger.info("Create with URI reference — skipping: %s", obj)
        return True

    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return False

    inst_stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(inst_stmt).scalars().first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Create from untrusted/blocked instance: %s", domain)
        return False

    from app.core import federation_sync

    res = federation_sync.reconcile_activity(activity)
    logger.info("Create activity reconciliation result: %s", res.get("status"))
    return True


def handle_update(activity: dict[str, Any]) -> bool:
    """Handle Update activity — merge remote metadata updates."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    if isinstance(obj, str):
        return True

    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return False

    inst_stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(inst_stmt).scalars().first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Update from untrusted/blocked instance: %s", domain)
        return False

    from app.core import federation_sync

    res = federation_sync.reconcile_activity(activity)
    logger.info("Update activity reconciliation result: %s", res.get("status"))
    return True


def handle_delete(activity: dict[str, Any]) -> bool:
    """Handle Delete activity — remove deleted actor and relationships."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    object_uri = obj if isinstance(obj, str) else obj.get("id", "")
    if not object_uri:
        return False

    # Prevent actor deletion spoofing: actor can only delete itself
    if actor_uri != object_uri:
        logger.warning("Delete spoofing attempt: actor %s tried to delete %s", actor_uri, object_uri)
        return False

    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if domain:
        inst_stmt = select(FederationInstance).where(FederationInstance.domain == domain)
        instance = db.session.execute(inst_stmt).scalars().first()
        if instance and instance.trust_level == TrustLevel.BLOCKED:
            return False

    stmt = select(FederationActor).where(FederationActor.actor_uri == object_uri)
    remote_actor = db.session.execute(stmt).scalars().first()
    if remote_actor:
        followers = (
            db.session.execute(select(FederationFollower).where(FederationFollower.remote_actor_id == remote_actor.id)).scalars().all()
        )
        for f in followers:
            db.session.delete(f)
        db.session.delete(remote_actor)
        db.session.commit()
        logger.info("Removed deleted remote actor: %s", object_uri)
        return True

    return True


def handle_announce(activity: dict[str, Any]) -> bool:
    """Handle Announce (boost) activity."""
    actor_uri = activity.get("actor", "")
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return False

    inst_stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(inst_stmt).scalars().first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Announce from untrusted/blocked instance: %s", domain)
        return False

    return True
