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
"""Feedback submission and local ticket management endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Any

from flask import Response, g, jsonify, request
from sqlalchemy import desc, func, select

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.db.models import FeedbackItem, User, db
from app.utils.images import save_upload_image, validate_upload_file

_TYPES = {"feature_request", "bug"}
_STATUSES = {"new", "accepted", "in_progress", "in_validation", "closed"}


def _can_admin_tickets(user: User | None) -> bool:
    if not user:
        return False
    return bool(any(role.name == "admin" for role in user.roles) or user.has_permission(PermissionName.TICKETS_ADMIN))


def _can_create_tickets(user: User | None) -> bool:
    if not user:
        return False
    return bool(any(role.name in {"admin", "user"} for role in user.roles) or user.has_permission(PermissionName.TICKETS_CREATOR))


@api_bp.route("/feedback", methods=["POST"])
@require_auth
@limiter.limit("5 per hour", override_defaults=True)
def submit_feedback() -> tuple[Response, int] | Response:
    """Create a feedback ticket, optionally storing multiple screenshots."""
    user = db.session.get(User, g.user_id)
    if not _can_create_tickets(user) and not _can_admin_tickets(user):
        return jsonify({"success": False, "error": "Insufficient permissions to submit feedback"}), 403

    feedback_type = request.form.get("type", "").strip()
    description = request.form.get("description", "").strip()
    if feedback_type not in _TYPES:
        return jsonify({"success": False, "error": "type must be feature_request or bug"}), 400
    if not description or len(description) > 20_000:
        return jsonify({"success": False, "error": "description is required and must be at most 20000 characters"}), 400

    uploads = request.files.getlist("screenshots")
    if len(uploads) > 5:
        return jsonify({"success": False, "error": "Maximum 5 screenshots allowed per ticket"}), 400

    attachments: list[str] = []
    try:
        for upload in uploads:
            validate_upload_file(upload, max_size_bytes=10 * 1024 * 1024)
            attachments.append(save_upload_image(upload, subfolder="gallery", filename=f"feedback-{uuid.uuid4().hex}.jpg"))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    item = FeedbackItem(user_id=g.user_id, feedback_type=feedback_type, description=description, attachments=attachments)
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "data": item.to_dict()}), 201


@api_bp.route("/feedback", methods=["GET"])
@require_auth
@limiter.limit("60 per minute")
def list_feedback() -> tuple[Response, int] | Response:
    """List the current user's tickets, or all tickets for administrators."""
    user = db.session.get(User, g.user_id)
    if not user or (not _can_admin_tickets(user) and not _can_create_tickets(user)):
        return jsonify({"success": False, "error": "Insufficient permissions to view tickets"}), 403

    stmt = select(FeedbackItem)
    is_admin = _can_admin_tickets(user)
    if not is_admin:
        stmt = stmt.where(FeedbackItem.user_id == g.user_id)
    else:
        req_user_id = request.args.get("user_id")
        if req_user_id:
            try:
                target_uuid = uuid.UUID(req_user_id)
                stmt = stmt.where(FeedbackItem.user_id == target_uuid)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid user_id filter"}), 400

    feedback_type = request.args.get("type")
    status = request.args.get("status")
    if feedback_type:
        if feedback_type not in _TYPES:
            return jsonify({"success": False, "error": "Invalid feedback type"}), 400
        stmt = stmt.where(FeedbackItem.feedback_type == feedback_type)
    if status:
        if status not in _STATUSES:
            return jsonify({"success": False, "error": "Invalid feedback status"}), 400
        stmt = stmt.where(FeedbackItem.status == status)

    page = max(1, request.args.get("page", 1, type=int))
    per_page = max(1, min(request.args.get("per_page", 20, type=int), 100))

    count_stmt = select(func.count()).select_from(stmt.subquery())  # pylint: disable=not-callable
    total = db.session.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(desc(FeedbackItem.created_at)).offset((page - 1) * per_page).limit(per_page)
    items = db.session.execute(stmt).scalars().all()

    return jsonify(
        {
            "success": True,
            "data": [item.to_dict() for item in items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if per_page else 1,
            },
        }
    )


@api_bp.route("/feedback/<int:feedback_id>", methods=["GET"])
@require_auth
@limiter.limit("60 per minute")
def get_feedback_item(feedback_id: int) -> tuple[Response, int] | Response:
    """Retrieve details for a single feedback ticket."""
    user = db.session.get(User, g.user_id)
    item = db.session.get(FeedbackItem, feedback_id)
    if not item:
        return jsonify({"success": False, "error": "Feedback item not found"}), 404

    is_admin = _can_admin_tickets(user)
    if not is_admin and item.user_id != g.user_id:
        return jsonify({"success": False, "error": "Forbidden"}), 403

    return jsonify({"success": True, "data": item.to_dict()})


@api_bp.route("/feedback/<int:feedback_id>", methods=["PATCH"])
@require_auth
@limiter.limit("30 per minute")
def update_feedback(feedback_id: int) -> tuple[Response, int] | Response:
    """Update a ticket's lifecycle status or add a comment."""
    user = db.session.get(User, g.user_id)
    item = db.session.get(FeedbackItem, feedback_id)
    if not item:
        return jsonify({"success": False, "error": "Feedback item not found"}), 404

    is_admin = _can_admin_tickets(user)
    is_owner = item.user_id == g.user_id

    if not is_admin and not is_owner:
        return jsonify({"success": False, "error": "Forbidden"}), 403

    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    comment_text = body.get("comment", "").strip() if isinstance(body.get("comment"), str) else ""

    if new_status is not None:
        if new_status not in _STATUSES:
            return jsonify({"success": False, "error": "Invalid feedback status"}), 400
        if not is_admin and new_status != "closed":
            return jsonify({"success": False, "error": "Creators may only close their tickets"}), 403
        item.status = new_status

    if comment_text:
        if item.status == "closed":
            return jsonify({"success": False, "error": "Cannot add comments to a closed ticket"}), 400
        comment_entry: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "user_id": str(g.user_id),
            "user_display_name": user.display_name if user else "User",
            "comment": comment_text,
            "created_at": datetime.now(UTC).isoformat(),
        }
        item.comments = list(item.comments or []) + [comment_entry]

    item.updated_at = datetime.now(UTC)
    db.session.commit()
    return jsonify({"success": True, "data": item.to_dict()})
