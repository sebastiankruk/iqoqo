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
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

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
    except (ValueError, KeyError, TypeError, AttributeError):
        logger.exception("Error handling %s activity", activity_type)
        return False


def _get_or_create_actor(actor_uri: str) -> FederationActor | None:
    """Get or create a FederationActor record for the given URI."""
    actor = FederationActor.query.filter_by(actor_uri=actor_uri).first()
    if actor:
        return actor  # type: ignore[no-any-return]

    # Create a stub actor — will be fully populated by fetch_actor later
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return None

    # Get or create instance
    instance = FederationInstance.query.filter_by(domain=domain).first()
    if not instance:
        default_trust = ConfigService.get("FEDERATION_DEFAULT_TRUST", TrustLevel.UNTRUSTED)
        instance = FederationInstance(domain=domain, trust_level=str(default_trust))
        db.session.add(instance)
        db.session.flush()

    actor = FederationActor(
        actor_uri=actor_uri,
        inbox_url=f"{actor_uri}/inbox",
        instance_id=instance.id,
        last_fetched_at=datetime.now(UTC),
    )
    db.session.add(actor)
    db.session.flush()
    return actor


def handle_follow(activity: dict[str, Any]) -> bool:
    """Handle a Follow activity — remote actor wants to follow local user.

    Auto-accepts if the instance trust level is 'trusted' and auto-accept is enabled.
    """
    actor_uri = activity.get("actor", "")
    object_uri = activity.get("object", "")

    if not actor_uri or not object_uri:
        return False

    # Extract username from object URI
    # Expected format: https://instance/api/federation/actor/{username}
    parts = object_uri.rstrip("/").split("/")
    username = parts[-1] if parts else None

    if not username:
        return False

    user = User.query.filter_by(public_username=username).first()
    if not user:
        logger.warning("Follow target user not found: %s", username)
        return False

    # Check consent
    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_profile:
        logger.info("Follow rejected — user %s has no federation consent", username)
        return False

    # Get or create remote actor
    remote_actor = _get_or_create_actor(actor_uri)
    if not remote_actor:
        return False

    # Check if follow already exists
    existing = FederationFollower.query.filter_by(
        local_user_id=user.id,
        remote_actor_id=remote_actor.id,
    ).first()

    if existing:
        existing.status = FollowStatus.PENDING
    else:
        follower = FederationFollower(
            local_user_id=user.id,
            remote_actor_id=remote_actor.id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)

    db.session.commit()

    # Auto-accept if trusted instance and auto-accept enabled
    auto_accept = ConfigService.get("FEDERATION_AUTO_ACCEPT_FOLLOWS", False)
    if isinstance(auto_accept, str):
        auto_accept = auto_accept.lower() in {"true", "1", "yes"}

    instance = remote_actor.instance
    if auto_accept and instance and instance.trust_level == TrustLevel.TRUSTED:
        _accept_follow(user, remote_actor, activity)

    return True


def _accept_follow(user: User, remote_actor: FederationActor, original_activity: dict[str, Any]) -> None:
    """Accept a follow request and send Accept activity back."""
    follower = FederationFollower.query.filter_by(
        local_user_id=user.id,
        remote_actor_id=remote_actor.id,
    ).first()

    if follower:
        follower.status = FollowStatus.ACCEPTED
        db.session.commit()

    # Queue Accept activity for delivery
    from app.core.federation_dispatch import dispatch_accept_follow

    dispatch_accept_follow(user, remote_actor, original_activity)


def handle_undo(activity: dict[str, Any]) -> bool:
    """Handle an Undo activity — typically Undo(Follow)."""
    inner = activity.get("object", {})
    if isinstance(inner, str):
        # Can't undo a bare URI reference
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

    parts = object_uri.rstrip("/").split("/")
    username = parts[-1] if parts else None
    if not username:
        return False

    user = User.query.filter_by(public_username=username).first()
    if not user:
        return False

    remote_actor = FederationActor.query.filter_by(actor_uri=actor_uri).first()
    if not remote_actor:
        return False

    follower = FederationFollower.query.filter_by(
        local_user_id=user.id,
        remote_actor_id=remote_actor.id,
    ).first()

    if follower:
        db.session.delete(follower)
        db.session.commit()

    return True


def handle_accept(activity: dict[str, Any]) -> bool:
    """Handle Accept activity (response to our Follow request).

    Updates the local outbound follow request status to ACCEPTED.
    """
    actor_uri = activity.get("actor", "")
    inner = activity.get("object", {})

    # Extract the original Follow's object (which is our local actor URI)
    if isinstance(inner, dict) and inner.get("type") == "Follow":
        followed_uri = inner.get("actor", "")
    else:
        logger.info("Received Accept without Follow inner object from %s", actor_uri)
        return True

    # Find the remote actor who accepted
    remote_actor = FederationActor.query.filter_by(actor_uri=actor_uri).first()
    if not remote_actor:
        return True

    # Find local user from the followed_uri
    # Format: https://instance/api/federation/actor/{username}
    parts = followed_uri.rstrip("/").split("/")
    username = parts[-1] if parts else None
    if not username:
        return True

    user = User.query.filter_by(public_username=username).first()
    if not user:
        return True

    # Update follower status to accepted
    follower = FederationFollower.query.filter_by(
        local_user_id=user.id,
        remote_actor_id=remote_actor.id,
    ).first()

    if follower:
        follower.status = FollowStatus.ACCEPTED
        db.session.commit()
        logger.info("Follow accepted by %s for user %s", actor_uri, username)

    return True


def handle_reject(activity: dict[str, Any]) -> bool:
    """Handle Reject activity (response to our Follow request).

    Updates the local outbound follow request status to REJECTED and removes it.
    """
    actor_uri = activity.get("actor", "")
    inner = activity.get("object", {})

    if isinstance(inner, dict) and inner.get("type") == "Follow":
        followed_uri = inner.get("actor", "")
    else:
        logger.info("Received Reject without Follow inner object from %s", actor_uri)
        return True

    remote_actor = FederationActor.query.filter_by(actor_uri=actor_uri).first()
    if not remote_actor:
        return True

    parts = followed_uri.rstrip("/").split("/")
    username = parts[-1] if parts else None
    if not username:
        return True

    user = User.query.filter_by(public_username=username).first()
    if not user:
        return True

    follower = FederationFollower.query.filter_by(
        local_user_id=user.id,
        remote_actor_id=remote_actor.id,
    ).first()

    if follower:
        follower.status = FollowStatus.REJECTED
        db.session.commit()
        logger.info("Follow rejected by %s for user %s", actor_uri, username)

    return True


def handle_create(activity: dict[str, Any]) -> bool:
    """Handle Create activity — receive remote collection or metadata updates."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    if isinstance(obj, str):
        logger.info("Create with URI reference — skipping: %s", obj)
        return True

    # Check trust level before processing
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    instance = FederationInstance.query.filter_by(domain=domain).first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Create from untrusted/blocked instance: %s", domain)
        return False

    # Queue for metadata sync if from trusted peer
    if instance.trust_level == TrustLevel.TRUSTED:
        from app.core.federation_sync import sync_remote_object

        sync_remote_object(obj, instance)

    return True


def handle_update(activity: dict[str, Any]) -> bool:
    """Handle Update activity — merge remote metadata updates."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    if isinstance(obj, str):
        return True

    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    instance = FederationInstance.query.filter_by(domain=domain).first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Update from untrusted/blocked instance: %s", domain)
        return False

    if instance.trust_level == TrustLevel.TRUSTED:
        from app.core.federation_sync import sync_remote_object

        sync_remote_object(obj, instance)

    return True


def handle_delete(activity: dict[str, Any]) -> bool:
    """Handle Delete activity — mark remote-sourced metadata as deleted.

    Removes the cached FederationActor if the deleted object is an actor,
    and marks any pending activities from that actor as failed.
    """
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", {})

    object_uri = obj if isinstance(obj, str) else obj.get("id", "")
    if not object_uri:
        return False

    # Check trust level
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    instance = FederationInstance.query.filter_by(domain=domain).first()

    if not instance or instance.trust_level == TrustLevel.BLOCKED:
        return False

    # If the deleted object is an actor, remove from cache and followers
    remote_actor = FederationActor.query.filter_by(actor_uri=object_uri).first()
    if remote_actor:
        # Remove all follow relationships with this actor
        FederationFollower.query.filter_by(remote_actor_id=remote_actor.id).delete()
        db.session.delete(remote_actor)
        db.session.commit()
        logger.info("Removed deleted remote actor: %s", object_uri)
        return True

    # For non-actor objects, mark any queued sync activities for this object as failed
    from app.db.federation import ActivityStatus, FederationActivity

    pending_activities = FederationActivity.query.filter(
        FederationActivity.object_json.contains(object_uri) if hasattr(FederationActivity.object_json, "contains") else db.literal(True),
        FederationActivity.status == ActivityStatus.QUEUED,
        FederationActivity.direction == "inbound",
    ).all()

    for act in pending_activities:
        act.status = ActivityStatus.FAILED
    if pending_activities:
        db.session.commit()

    logger.info("Processed Delete for %s from %s", object_uri, actor_uri)
    return True


def handle_announce(activity: dict[str, Any]) -> bool:
    """Handle Announce (boost) activity — propagate to local followers if trusted."""
    actor_uri = activity.get("actor", "")
    obj = activity.get("object", "")

    # Check trust level
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    instance = FederationInstance.query.filter_by(domain=domain).first()

    if not instance or instance.trust_level in (TrustLevel.UNTRUSTED, TrustLevel.BLOCKED):
        logger.info("Ignoring Announce from untrusted/blocked instance: %s", domain)
        return False

    object_uri = obj if isinstance(obj, str) else obj.get("id", "")
    logger.info("Received Announce for %s from %s (trust: %s)", object_uri, actor_uri, instance.trust_level)
    return True
