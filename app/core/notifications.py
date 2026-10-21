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
"""In-app notifications dispatcher service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db import db
from app.db.social import Notification

logger = logging.getLogger(__name__)


def create_notification(
    user_id: uuid.UUID | str,
    notification_type: str,
    payload: dict[str, Any] | None = None,
    actor_uri: str | None = None,
    target_iri: str | None = None,
) -> Notification | None:
    """Create and persist an in-app notification for a user.

    Args:
        user_id: UUID of recipient user.
        notification_type: Categorical notification type (e.g. 'follow_request', 'loan_request', 'escalation_resolved').
        payload: Metadata for UI rendering and direct actions.
        actor_uri: ActivityPub actor URI or user IRI that originated the event.
        target_iri: URI of target item, work, or entity.

    Returns:
        Persisted Notification record, or None on failure.
    """
    try:
        parsed_user_id = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        notification = Notification(
            user_id=parsed_user_id,
            type=str(notification_type),
            actor_uri=str(actor_uri) if actor_uri else None,
            target_iri=str(target_iri) if target_iri else None,
            payload_json=payload or {},
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        logger.warning("Failed to persist notification for user %s: %s", user_id, exc)
        return None
