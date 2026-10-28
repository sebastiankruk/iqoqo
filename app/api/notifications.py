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
"""In-app notifications REST API endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import func, select, update

from app.api.decorators import require_auth
from app.core.limiter import limiter
from app.db import db
from app.db.social import Notification

logger = logging.getLogger(__name__)

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


@notifications_bp.route("", methods=["GET"])
@require_auth
@limiter.limit("60 per minute")
def list_notifications() -> Response | tuple[Response, int]:
    """List in-app notifications for authenticated user with pagination."""
    user_id = g.user_id
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    limit_param = request.args.get("limit", default=20, type=int)
    offset_param = request.args.get("offset", default=0, type=int)
    unread_only = request.args.get("unread_only", default="false").lower() in {"true", "1", "yes"}

    limit = max(1, min(limit_param, 100))
    offset = max(0, offset_param)

    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    count_query = select(func.count()).select_from(query.subquery())  # pylint: disable=not-callable
    total = db.session.execute(count_query).scalar() or 0

    unread_count_query = select(func.count()).select_from(  # pylint: disable=not-callable
        select(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).subquery()
    )
    unread_total = db.session.execute(unread_count_query).scalar() or 0

    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    notifications = db.session.execute(query).scalars().all()

    return (
        jsonify(
            {
                "notifications": [n.to_dict() for n in notifications],
                "total": total,
                "unread_count": unread_total,
                "limit": limit,
                "offset": offset,
            }
        ),
        200,
    )


@notifications_bp.route("/read", methods=["PATCH"])
@require_auth
@limiter.limit("60 per minute")
def mark_notifications_read() -> Response | tuple[Response, int]:
    """Mark specific notification ids as read."""
    user_id = g.user_id
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    payload = request.get_json(silent=True) or {}
    notification_ids = payload.get("notification_ids") or []
    if not isinstance(notification_ids, list):
        return jsonify({"error": "notification_ids must be a list", "code": 400}), 400

    if not notification_ids:
        return jsonify({"marked_count": 0}), 200

    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.id.in_(notification_ids),
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    result = db.session.execute(stmt)
    db.session.commit()

    return jsonify({"marked_count": result.rowcount}), 200


@notifications_bp.route("/read-all", methods=["POST"])
@require_auth
@limiter.limit("60 per minute")
def mark_all_notifications_read() -> Response | tuple[Response, int]:
    """Mark all unread notifications for the user as read."""
    user_id = g.user_id
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    result = db.session.execute(stmt)
    db.session.commit()

    return jsonify({"marked_count": result.rowcount}), 200
