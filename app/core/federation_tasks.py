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
"""Celery tasks for federation — async inbox processing and outbound delivery.

These functions can be dispatched via submit_task() for true async execution
when Celery/Redis is available, or called inline as a fallback.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def process_inbound_activity(activity_id: str, activity: dict[str, Any]) -> bool:
    """Process an inbound activity asynchronously.

    Called from the inbox endpoint after initial validation.
    Dispatched via submit_task() for Celery execution when available.

    Args:
        activity_id: The FederationActivity UUID string.
        activity: The parsed activity JSON.

    Returns:
        True if processed successfully.
    """
    from app.core.federation_handlers import handle_activity
    from app.db import db
    from app.db.federation import ActivityStatus, FederationActivity

    success = handle_activity(activity)

    # Update activity status
    pk = uuid_mod.UUID(activity_id) if isinstance(activity_id, str) else activity_id
    fed_activity = db.session.get(FederationActivity, pk)
    if fed_activity:
        fed_activity.status = ActivityStatus.DELIVERED if success else ActivityStatus.FAILED
        fed_activity.delivered_at = datetime.now(UTC)
        db.session.commit()

    return success


def deliver_activity(
    activity_id: str,
    target_inbox_url: str,
    activity: dict[str, Any],
    sender_user_id: str,
    actor_key_id: str,
) -> bool:
    """Deliver an outbound activity to a remote inbox.

    Dispatched via submit_task() for Celery execution when available.
    Retries up to 3 times on transient failures.

    Args:
        activity_id: The FederationActivity UUID string.
        target_inbox_url: Remote inbox URL.
        activity: The activity JSON to send.
        sender_user_id: UUID of the local sender.
        actor_key_id: Full key ID URI for signing.

    Returns:
        True if delivery succeeded.
    """
    from app.core.federation_client import FederationDeliveryError, SSRFError, federation_client
    from app.db import db
    from app.db.federation import ActivityStatus, FederationActivity

    pk = uuid_mod.UUID(activity_id) if isinstance(activity_id, str) else activity_id
    fed_activity = db.session.get(FederationActivity, pk)

    try:
        federation_client.post_to_inbox(target_inbox_url, activity, sender_user_id, actor_key_id)

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

    except FederationDeliveryError as exc:
        logger.warning("Delivery failed to %s: %s", target_inbox_url, exc)
        if fed_activity:
            fed_activity.retry_count += 1
            if fed_activity.retry_count >= 3:
                fed_activity.status = ActivityStatus.FAILED
            db.session.commit()
        return False
