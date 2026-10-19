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
"""Celery tasks for federation — async inbox processing and outbound delivery."""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

from app.db import db
from app.db.federation import ActivityStatus, FederationActivity
from app.utils.http_client import SSRFError

logger = logging.getLogger(__name__)


def process_inbound_activity(activity_id: str, activity: dict[str, Any]) -> bool:
    """Process an inbound activity asynchronously.

    Args:
        activity_id: The FederationActivity UUID string.
        activity: The parsed activity JSON.

    Returns:
        True if processed successfully, False otherwise.
    """
    from app.core.federation_handlers import handle_activity

    success = False
    try:
        success = handle_activity(activity)
    except Exception as exc:
        logger.exception("Error executing activity handler for %s: %s", activity_id, exc)
        success = False

    try:
        pk = uuid_mod.UUID(activity_id) if isinstance(activity_id, str) else activity_id
        fed_activity = db.session.get(FederationActivity, pk)
        if fed_activity:
            fed_activity.status = ActivityStatus.DELIVERED if success else ActivityStatus.FAILED
            fed_activity.delivered_at = datetime.now(UTC)
            db.session.commit()
    except Exception as exc:
        logger.error("Failed to update status for activity %s: %s", activity_id, exc)
        db.session.rollback()

    return success


def deliver_activity(
    activity_id: str,
    target_inbox_url: str,
    activity: dict[str, Any],
    sender_user_id: str,
    actor_key_id: str,
) -> bool:
    """Deliver an outbound activity to a remote inbox.

    Args:
        activity_id: The FederationActivity UUID string.
        target_inbox_url: Remote inbox URL.
        activity: The activity JSON to send.
        sender_user_id: UUID of the local sender.
        actor_key_id: Full key ID URI for signing.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    from app.core.federation_client import FederationClient

    pk = uuid_mod.UUID(activity_id) if isinstance(activity_id, str) else activity_id
    fed_activity = db.session.get(FederationActivity, pk)

    client = FederationClient()
    try:
        client.post_to_inbox(target_inbox_url, activity, sender_user_id, actor_key_id)

        if fed_activity:
            fed_activity.status = ActivityStatus.DELIVERED
            fed_activity.delivered_at = datetime.now(UTC)
            db.session.commit()
        return True

    except SSRFError as exc:
        logger.error("SSRF blocked delivery to %s: %s", target_inbox_url, exc)
        if fed_activity:
            fed_activity.status = ActivityStatus.FAILED
            db.session.commit()
        return False

    except Exception as exc:
        logger.warning("Delivery failed to %s: %s", target_inbox_url, exc)
        if fed_activity:
            fed_activity.retry_count += 1
            if fed_activity.retry_count >= 3:
                fed_activity.status = ActivityStatus.FAILED
            db.session.commit()
        return False
