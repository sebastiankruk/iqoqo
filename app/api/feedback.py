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

import os
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any

from flask import Response, g, jsonify, request, send_from_directory
from pydantic import ValidationError
from sqlalchemy import desc, func, select
from werkzeug.utils import secure_filename

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.api.schemas import FeedbackUpdateSchema
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.core.tasks import upload_feedback_screenshot
from app.db.models import FeedbackComment, FeedbackItem, User, db
from app.utils.covers import GALLERY_DIR
from app.utils.images import save_upload_image, validate_upload_file
from app.utils.rclone_utils import get_rclone_target

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
            filename = f"feedback-{uuid.uuid4().hex}.jpg"
            # save_upload_image returns /static/gallery/...
            _ = save_upload_image(upload, subfolder="gallery", filename=filename)
            attachments.append(filename)

            # Trigger Celery task
            local_path = os.path.join(GALLERY_DIR, filename)
            upload_feedback_screenshot.apply_async(args=[local_path, filename])
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    item = FeedbackItem(user_id=g.user_id, feedback_type=feedback_type, description=description, attachments=attachments)
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "data": _format_feedback_item(item)}), 201


def _format_feedback_item(item: FeedbackItem) -> dict[str, Any]:
    """Format a FeedbackItem dictionary with canonical API screenshot paths."""
    d = item.to_dict()
    d["attachments"] = [f"/api/feedback/screenshots/{att}" if not att.startswith("/") else att for att in (d.get("attachments") or [])]
    return d


def _validate_screenshot_access(filename: str) -> tuple[Response, int] | None:
    """Validate that the authenticated user can access the given screenshot."""
    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 401

    if not _can_admin_tickets(user):
        stmt = select(FeedbackItem).where(FeedbackItem.user_id == g.user_id)
        user_items = db.session.execute(stmt).scalars().all()
        if not any(filename in (item.attachments or []) for item in user_items):
            return jsonify({"success": False, "error": "Forbidden"}), 403
    return None


@api_bp.route("/feedback/screenshots/<path:filename>", methods=["GET"])
@require_auth
def get_feedback_screenshot(filename: str) -> tuple[Response, int] | Response:
    """Retrieve a feedback screenshot from local storage or rclone remote."""
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({"success": False, "error": "Invalid filename"}), 400

    access_err = _validate_screenshot_access(safe_name)
    if access_err:
        return access_err

    local_path = os.path.join(GALLERY_DIR, safe_name)
    if os.path.exists(local_path):
        return send_from_directory(GALLERY_DIR, safe_name)

    rclone_remote = os.environ.get("RCLONE_FEEDBACK_REMOTE")
    if not rclone_remote:
        return jsonify({"success": False, "error": "Screenshot not found locally and no remote configured"}), 404

    target = get_rclone_target(rclone_remote, "feedback", safe_name)
    try:
        result = subprocess.run(["rclone", "cat", "--", target], check=True, capture_output=True)
        return Response(result.stdout, mimetype="image/jpeg")
    except subprocess.CalledProcessError:
        return jsonify({"success": False, "error": "Screenshot not found"}), 404


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
            "data": [_format_feedback_item(item) for item in items],
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

    return jsonify({"success": True, "data": _format_feedback_item(item)})


def _validate_feedback_patch_permissions(
    data: FeedbackUpdateSchema, is_admin: bool, is_owner: bool, item_status: str
) -> tuple[str, int] | None:
    """Validate user permissions and status transition constraints for feedback patch."""
    if data.status is not None and not is_admin and data.status != "closed":
        return "Creators may only close their tickets", 403
    if data.feedback_type is not None and not is_admin:
        return "Only admins can change feedback type", 403
    if data.description is not None and not is_admin and not is_owner:
        return "Forbidden", 403
    if data.comment and data.comment.strip() and item_status == "closed":
        return "Cannot add comments to a closed ticket", 400
    return None


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

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        data = FeedbackUpdateSchema.model_validate(body)
    except ValidationError as exc:
        formatted_errors = [
            {"loc": err.get("loc", ()), "msg": err.get("msg", ""), "type": err.get("type", "")} for err in exc.errors(include_url=False)
        ]
        return jsonify({"success": False, "error": formatted_errors}), 400

    perm_err = _validate_feedback_patch_permissions(data, is_admin, is_owner, item.status)
    if perm_err:
        return jsonify({"success": False, "error": perm_err[0]}), perm_err[1]

    if data.status is not None:
        item.status = data.status
    if data.feedback_type is not None:
        item.feedback_type = data.feedback_type
    if data.description is not None:
        item.description = data.description

    if data.comment:
        comment_text = data.comment.strip()
        if comment_text:
            new_comment = FeedbackComment(
                feedback_item_id=item.id, user_id=g.user_id, comment_text=comment_text, created_at=datetime.now(UTC)
            )
            db.session.add(new_comment)

    item.updated_at = datetime.now(UTC)
    db.session.commit()

    return jsonify({"success": True, "data": _format_feedback_item(item)})
