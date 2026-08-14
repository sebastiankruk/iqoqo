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

from flask import g, jsonify, request

from app.api.core import api_bp
from app.api.decorators import admin_required, require_auth
from app.core.limiter import limiter
from app.db.models import FeedbackItem, User, db
from app.utils.images import save_upload_image, validate_upload_file

_TYPES = {"feature_request", "bug"}
_STATUSES = {"new", "accepted", "in_progress", "in_validation", "closed"}


def _is_admin(user: User | None) -> bool:
    return bool(user and any(role.name == "admin" for role in user.roles))


@api_bp.route("/feedback", methods=["POST"])
@require_auth
@limiter.limit("5 per hour", override_defaults=True)
def submit_feedback():
    """Create a feedback ticket, optionally storing multiple screenshots."""
    feedback_type = request.form.get("type", "").strip()
    description = request.form.get("description", "").strip()
    if feedback_type not in _TYPES:
        return jsonify({"success": False, "error": "type must be feature_request or bug"}), 400
    if not description or len(description) > 20_000:
        return jsonify({"success": False, "error": "description is required and must be at most 20000 characters"}), 400

    attachments: list[str] = []
    try:
        for upload in request.files.getlist("screenshots"):
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
def list_feedback():
    """List the current user's tickets, or all tickets for administrators."""
    user = db.session.get(User, g.user_id)
    query = FeedbackItem.query
    if not _is_admin(user):
        query = query.filter(FeedbackItem.user_id == g.user_id)
    feedback_type = request.args.get("type")
    status = request.args.get("status")
    if feedback_type:
        if feedback_type not in _TYPES:
            return jsonify({"success": False, "error": "Invalid feedback type"}), 400
        query = query.filter_by(feedback_type=feedback_type)
    if status:
        if status not in _STATUSES:
            return jsonify({"success": False, "error": "Invalid feedback status"}), 400
        query = query.filter_by(status=status)
    items = query.order_by(FeedbackItem.created_at.desc()).all()
    return jsonify({"success": True, "data": [item.to_dict() for item in items]})


@api_bp.route("/feedback/<int:feedback_id>", methods=["PATCH"])
@require_auth
@admin_required
def update_feedback(feedback_id: int):
    """Update a ticket's lifecycle status."""
    item = db.session.get(FeedbackItem, feedback_id)
    if not item:
        return jsonify({"success": False, "error": "Feedback item not found"}), 404
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in _STATUSES:
        return jsonify({"success": False, "error": "Invalid feedback status"}), 400
    item.status = status
    item.updated_at = datetime.now(UTC)
    db.session.commit()
    return jsonify({"success": True, "data": item.to_dict()})
