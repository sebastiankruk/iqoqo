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

from sqlalchemy import select

from app.core.iri import canonical_actor_iri, get_federation_base_url
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


def dispatch_collection_update(user: User, item: Any, action: str = "Create") -> None:
    """Generate a Create or Delete activity when a user adds/removes an item.

    Args:
        user: The local user performing the action.
        item: The item being added/removed.
        action: "Create" or "Delete".
    """
    if getattr(item, "is_hidden", False):
        return

    consent_stmt = select(FederationConsent).where(FederationConsent.user_id == user.id)
    consent = db.session.execute(consent_stmt).scalars().first()
    if not consent or not consent.federated_collection:
        return

    base_url = get_federation_base_url()
    actor_url = canonical_actor_iri(user.id, base_url)

    manif = getattr(item, "manifestation", None)
    obj_payload: dict[str, Any] = {
        "type": "Document" if manif else "Note",
        "id": f"{base_url}/api/items/{item.id}" if hasattr(item, "id") else "",
        "attributedTo": actor_url,
        "content": f"Collection update: {action}",
    }
    if manif:
        if manif.isbn13:
            obj_payload["isbn13"] = manif.isbn13
        if manif.publisher:
            obj_payload["publisher"] = manif.publisher
        if manif.publication_date:
            obj_payload["publication_date"] = str(manif.publication_date)
        if manif.cover_url:
            obj_payload["cover_url"] = manif.cover_url
        if manif.format:
            obj_payload["format"] = manif.format

    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": action,
        "actor": actor_url,
        "object": obj_payload,
    }

    _queue_and_deliver(user, actor_url, activity)


def dispatch_metadata_update(user: User, manifestation: Any) -> None:
    """Broadcast metadata enrichment to followers.

    Args:
        user: The local user whose metadata was enriched.
        manifestation: The manifestation that was updated.
    """
    consent_stmt = select(FederationConsent).where(FederationConsent.user_id == user.id)
    consent = db.session.execute(consent_stmt).scalars().first()
    if not consent or not consent.federated_collection:
        return

    base_url = get_federation_base_url()
    actor_url = canonical_actor_iri(user.id, base_url)

    obj_payload: dict[str, Any] = {
        "type": "Document",
        "id": f"{base_url}/api/manifestations/{manifestation.id}" if hasattr(manifestation, "id") else "",
        "attributedTo": actor_url,
    }
    if manifestation.isbn13:
        obj_payload["isbn13"] = manifestation.isbn13
    if manifestation.publisher:
        obj_payload["publisher"] = manifestation.publisher
    if manifestation.publication_date:
        obj_payload["publication_date"] = str(manifestation.publication_date)
    if manifestation.cover_url:
        obj_payload["cover_url"] = manifestation.cover_url
    if manifestation.format:
        obj_payload["format"] = manifestation.format

    activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Update",
        "actor": actor_url,
        "object": obj_payload,
    }

    _queue_and_deliver(user, actor_url, activity)


def dispatch_accept_follow(user: User, remote_actor: FederationActor, original_activity: dict[str, Any]) -> None:
    """Send an Accept activity in response to a Follow.

    Args:
        user: The local user accepting the follow.
        remote_actor: The remote actor who sent the follow.
        original_activity: The original Follow activity.
    """
    base_url = get_federation_base_url()
    actor_url = canonical_actor_iri(user.id, base_url)

    accept_activity = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "Accept",
        "actor": actor_url,
        "object": original_activity,
    }

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

    from app.core.federation_tasks import deliver_activity
    from app.core.tasks import submit_task

    key_id = f"{actor_url}#main-key"
    task_id = submit_task(
        deliver_activity,
        str(fed_activity.id),
        remote_actor.inbox_url,
        accept_activity,
        str(user.id),
        key_id,
        queue="federation",
    )
    if not task_id:
        deliver_activity(
            str(fed_activity.id),
            remote_actor.inbox_url,
            accept_activity,
            str(user.id),
            key_id,
        )


def _queue_and_deliver(user: User, actor_url: str, activity: dict[str, Any]) -> None:
    """Queue an activity for fan-out delivery to all followers."""
    from app.core.federation_tasks import deliver_activity
    from app.core.tasks import submit_task

    # Join FederationActor in initial query to eliminate N+1 loop queries
    stmt = (
        select(FederationFollower, FederationActor)
        .join(FederationActor, FederationFollower.remote_actor_id == FederationActor.id)
        .where(
            FederationFollower.local_user_id == user.id,
            FederationFollower.status == FollowStatus.ACCEPTED,
        )
    )
    pairs = db.session.execute(stmt).all()
    if not pairs:
        return

    key_id = f"{actor_url}#main-key"
    created_activities: list[tuple[FederationActivity, str]] = []

    for _follower, remote_actor in pairs:
        if not remote_actor or not remote_actor.inbox_url:
            continue

        fed_activity = FederationActivity(
            actor_uri=actor_url,
            activity_type=activity.get("type", "Unknown"),
            object_json=activity,
            target_uri=remote_actor.inbox_url,
            direction="outbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(fed_activity)
        created_activities.append((fed_activity, remote_actor.inbox_url))

    # Commit records to database BEFORE enqueuing to Celery to prevent race condition
    db.session.commit()

    for fed_activity, inbox_url in created_activities:
        task_id = submit_task(
            deliver_activity,
            str(fed_activity.id),
            inbox_url,
            activity,
            str(user.id),
            key_id,
            queue="federation",
        )
        if not task_id:
            deliver_activity(
                str(fed_activity.id),
                inbox_url,
                activity,
                str(user.id),
                key_id,
            )
