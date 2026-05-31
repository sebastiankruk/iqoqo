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
"""Federation activity dispatch — generates and sends outbound activities."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config_service import ConfigService
from app.db import db
from app.db.auth import User
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationActor,
    FederationConsent,
    FederationFollower,
    FollowStatus,
)

logger = logging.getLogger(__name__)


def _get_base_url() -> str:
    """Get the federation base URL."""
    base_url = ConfigService.get("FEDERATION_BASE_URL", "http://localhost:3000")
    return str(base_url).rstrip("/")


def _get_actor_url(username: str) -> str:
    """Construct the actor URL for a local user."""
    return f"{_get_base_url()}/api/federation/actor/{username}"


def dispatch_collection_update(user: User, item: Any, action: str = "Create") -> None:
    """Generate a Create or Delete activity when a user adds/removes an item.

    Args:
        user: The local user performing the action.
        item: The item being added/removed.
        action: "Create" or "Delete".
    """
    # Check consent
    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_collection:
        return

    if not user.public_username:
        return

    actor_url = _get_actor_url(user.public_username)
    base_url = _get_base_url()

    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": action,
        "actor": actor_url,
        "object": {
            "type": "Note",
            "id": f"{base_url}/api/items/{item.id}" if hasattr(item, "id") else "",
            "attributedTo": actor_url,
            "content": f"Collection update: {action}",
        },
    }

    _queue_and_deliver(user, actor_url, activity)


def dispatch_metadata_update(user: User, manifestation: Any) -> None:
    """Broadcast metadata enrichment to followers.

    Args:
        user: The local user whose metadata was enriched.
        manifestation: The manifestation that was updated.
    """
    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_collection:
        return

    if not user.public_username:
        return

    actor_url = _get_actor_url(user.public_username)
    base_url = _get_base_url()

    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Update",
        "actor": actor_url,
        "object": {
            "type": "Document",
            "id": f"{base_url}/api/manifestations/{manifestation.id}" if hasattr(manifestation, "id") else "",
            "attributedTo": actor_url,
        },
    }

    _queue_and_deliver(user, actor_url, activity)


def dispatch_accept_follow(user: User, remote_actor: FederationActor, original_activity: dict[str, Any]) -> None:
    """Send an Accept activity in response to a Follow.

    Args:
        user: The local user accepting the follow.
        remote_actor: The remote actor who sent the follow.
        original_activity: The original Follow activity.
    """
    if not user.public_username:
        return

    actor_url = _get_actor_url(user.public_username)

    accept_activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Accept",
        "actor": actor_url,
        "object": original_activity,
    }

    # Log the activity
    fed_activity = FederationActivity(
        actor_uri=actor_url,
        activity_type="Accept",
        object_json=accept_activity,
        target_uri=remote_actor.inbox_url,
        direction="outbound",
        status=ActivityStatus.QUEUED,
    )
    db.session.add(fed_activity)
    db.session.commit()

    # Queue delivery
    from app.core.federation_tasks import deliver_activity
    from app.core.tasks import submit_task

    task_id = submit_task(
        deliver_activity,
        str(fed_activity.id),
        remote_actor.inbox_url,
        accept_activity,
        str(user.id),
        f"{actor_url}#main-key",
    )
    if not task_id:
        # Celery unavailable — deliver inline as fallback
        deliver_activity(
            str(fed_activity.id),
            remote_actor.inbox_url,
            accept_activity,
            str(user.id),
            f"{actor_url}#main-key",
        )


def _queue_and_deliver(user: User, actor_url: str, activity: dict[str, Any]) -> None:
    """Queue an activity for fan-out delivery to all followers."""
    from app.core.federation_tasks import deliver_activity
    from app.core.tasks import submit_task

    # Get all accepted followers
    followers = FederationFollower.query.filter_by(
        local_user_id=user.id,
        status=FollowStatus.ACCEPTED,
    ).all()

    if not followers:
        return

    for follower in followers:
        remote_actor = db.session.get(FederationActor, follower.remote_actor_id)
        if not remote_actor:
            continue

        # Log the activity for each delivery target
        fed_activity = FederationActivity(
            actor_uri=actor_url,
            activity_type=activity.get("type", "Unknown"),
            object_json=activity,
            target_uri=remote_actor.inbox_url,
            direction="outbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(fed_activity)
        db.session.flush()

        # Dispatch via Celery if available, otherwise deliver inline
        task_id = submit_task(
            deliver_activity,
            str(fed_activity.id),
            remote_actor.inbox_url,
            activity,
            str(user.id),
            f"{actor_url}#main-key",
        )
        if not task_id:
            # Celery unavailable — deliver inline as fallback
            deliver_activity(
                str(fed_activity.id),
                remote_actor.inbox_url,
                activity,
                str(user.id),
                f"{actor_url}#main-key",
            )

    db.session.commit()
