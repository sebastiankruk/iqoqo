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
"""Federation metadata synchronization — trust-gated reconciliation."""

from __future__ import annotations

import logging
from typing import Any

from app.db import db
from app.db.federation import FederationInstance, TrustLevel

logger = logging.getLogger(__name__)


def sync_remote_object(obj: dict[str, Any], instance: FederationInstance) -> bool:
    """Synchronize a remote object into the local catalog.

    Trust-level gating:
    - Trusted peers: auto-merge if local field is empty or older
    - Pending peers: queue for admin review
    - Untrusted/Blocked: ignore

    Args:
        obj: The ActivityStreams object (typically a Work/Manifestation representation).
        instance: The FederationInstance the object came from.

    Returns:
        True if sync was processed (even if queued for review).
    """
    if instance.trust_level == TrustLevel.BLOCKED:
        return False

    if instance.trust_level == TrustLevel.UNTRUSTED:
        return False

    if instance.trust_level == TrustLevel.PENDING:
        # Queue for admin review
        _queue_for_review(obj, instance)
        return True

    if instance.trust_level == TrustLevel.TRUSTED:
        # Auto-merge
        return _auto_merge(obj, instance)

    return False


def sync_manifestation(
    remote_data: dict[str, Any],
    local_manifestation: Any,
    instance: FederationInstance,
) -> bool:
    """Merge remote metadata into a local manifestation using trust-gated rules.

    Trusted peers: Remote updates overwrite local fields if local field is empty or older.
    Pending peers: Queue for admin review.
    Untrusted: Ignore.

    Args:
        remote_data: Remote manifestation metadata dict.
        local_manifestation: The local Manifestation ORM object.
        instance: The source FederationInstance.

    Returns:
        True if any fields were updated.
    """
    if instance.trust_level in (TrustLevel.BLOCKED, TrustLevel.UNTRUSTED):
        return False

    if instance.trust_level == TrustLevel.PENDING:
        _queue_for_review(remote_data, instance)
        return True

    # Trusted peer — merge non-empty remote fields into empty local fields
    updated = False
    mergeable_fields = ["title", "subtitle", "description", "cover_url", "isbn", "publisher", "year"]

    for field in mergeable_fields:
        remote_val = remote_data.get(field)
        if not remote_val:
            continue
        local_val = getattr(local_manifestation, field, None) if hasattr(local_manifestation, field) else None
        if not local_val:
            setattr(local_manifestation, field, remote_val)
            updated = True

    if updated:
        # Track provenance
        meta = getattr(local_manifestation, "meta", None) or {}
        meta["federation_source"] = instance.domain
        if hasattr(local_manifestation, "meta"):
            local_manifestation.meta = meta
        db.session.commit()
        logger.info(
            "Merged %d fields into manifestation %s from %s",
            sum(1 for f in mergeable_fields if remote_data.get(f) and not getattr(local_manifestation, f, None)),
            getattr(local_manifestation, "id", "?"),
            instance.domain,
        )

    return updated


def _queue_for_review(obj: dict[str, Any], instance: FederationInstance) -> None:
    """Queue a remote object for admin review.

    Stores as a pending FederationActivity for admin to approve/reject.
    """
    from app.db.federation import ActivityStatus, FederationActivity

    activity = FederationActivity(
        actor_uri=f"https://{instance.domain}",
        activity_type="PendingMerge",
        object_json={"object": obj, "source_instance": instance.domain},
        direction="inbound",
        status=ActivityStatus.QUEUED,
    )
    db.session.add(activity)
    db.session.commit()

    logger.info("Queued metadata merge from %s for admin review", instance.domain)


def _auto_merge(obj: dict[str, Any], instance: FederationInstance) -> bool:
    """Auto-merge metadata from a trusted peer.

    Attempts to find a matching local manifestation by ISBN or title,
    then merges non-empty remote fields into empty local fields.

    Args:
        obj: The remote object data.
        instance: The trusted source instance.

    Returns:
        True if merge was attempted.
    """
    obj_type = obj.get("type", "")
    obj_id = obj.get("id", "")

    logger.info(
        "Auto-merging %s (%s) from trusted instance %s",
        obj_type,
        obj_id,
        instance.domain,
    )

    # Attempt to find matching local manifestation
    isbn = obj.get("isbn") or obj.get("identifier")
    title = obj.get("title") or obj.get("name")

    if not isbn and not title:
        logger.debug("Cannot auto-merge: no ISBN or title in remote object")
        return True

    try:
        from app.db.catalog import Manifestation

        local = None
        if isbn:
            local = Manifestation.query.filter_by(isbn=isbn).first()
        if not local and title:
            local = Manifestation.query.filter(Manifestation.title.ilike(f"%{title}%")).first()

        if local:
            return sync_manifestation(obj, local, instance)

        logger.debug("No matching local manifestation for remote object %s", obj_id)
    except (ImportError, AttributeError):
        # Catalog model not available in this context
        logger.debug("Catalog model not available for auto-merge")

    return True


def propose_metadata_merge(remote_data: dict[str, Any], source_domain: str) -> int | None:
    """Create a pending merge request for admin review.

    Args:
        remote_data: The metadata to potentially merge.
        source_domain: Domain of the source instance.

    Returns:
        ID of the created FederationActivity or None.
    """
    from app.db.federation import ActivityStatus, FederationActivity

    activity = FederationActivity(
        actor_uri=f"https://{source_domain}",
        activity_type="PendingMerge",
        object_json=remote_data,
        direction="inbound",
        status=ActivityStatus.QUEUED,
    )
    db.session.add(activity)
    db.session.commit()

    return activity.id  # type: ignore[no-any-return]
