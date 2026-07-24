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

"""API routes for social feedback (ratings and comments) on FRBR levels."""

import re
from datetime import UTC, datetime

from flask import Response, g, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.core import api_bp
from app.api.decorators import require_auth, require_permission
from app.core.permissions import PermissionName
from app.db.models import EscalationRequest, Expression, Item, Manifestation, SocialFeedback, SocialNote, Work, db

VALID_LEVELS = {"work", "expression", "manifestation", "item"}

# Defense-in-depth ceiling for free-text social content. Notes/comments are
# rendered as plain text on the frontend (no dangerouslySetInnerHTML), but we
# still cap length (storage/DoS hardening) and strip markup at ingress in case
# a future rendering path relaxes that assumption.
MAX_SOCIAL_TEXT_LENGTH = 2048

_TAG_RE = re.compile(r"<[^>]*>")


def _sanitize_text(value: str) -> str:
    """Strip HTML-like markup from free-text user input (defense in depth)."""
    return _TAG_RE.sub("", value).strip()


def _validate_note_input(data: dict | None) -> tuple[str | None, str | None]:
    """Validate note content in request data, returning (note_text, error_message)."""
    if not data or "note" not in data:
        return None, "Missing note content"
    note_text = _sanitize_text(str(data["note"]))
    if not note_text:
        return None, "Note content cannot be empty"
    if len(note_text) > MAX_SOCIAL_TEXT_LENGTH:
        return None, f"Note must be at most {MAX_SOCIAL_TEXT_LENGTH} characters"
    return note_text, None


def _verify_target_exists(level: str, target_id: int) -> bool:
    """Helper to verify that the target FRBR resource exists in the database."""
    if level == "work":
        return db.session.get(Work, target_id) is not None
    if level == "expression":
        return db.session.get(Expression, target_id) is not None
    if level == "manifestation":
        return db.session.get(Manifestation, target_id) is not None
    if level == "item":
        return db.session.get(Item, target_id) is not None
    return False


@api_bp.route("/feedback/<string:level>/<int:target_id>", methods=["GET"])
def get_social_feedback(level: str, target_id: int) -> Response | tuple[Response, int]:
    """
    Get all social feedback (ratings and comments) for a specific FRBR level and resource ID.
    Also returns aggregated statistics like average rating.
    """
    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {list(VALID_LEVELS)}", "code": 400}), 400

    if not _verify_target_exists(level, target_id):
        return jsonify({"error": f"{level.capitalize()} not found", "code": 404}), 404

    # Fetch feedbacks using SQLAlchemy 2.0 style syntax with selectinload to avoid N+1 queries
    column_name = f"{level}_id"
    stmt = (
        select(SocialFeedback)
        .options(selectinload(SocialFeedback.user))  # type: ignore[arg-type]
        .where(getattr(SocialFeedback, column_name) == target_id)
        .order_by(SocialFeedback.created_at.desc())
    )
    feedbacks = db.session.execute(stmt).scalars().all()

    # Prefer GROUP BY aggregate queries to avoid N+1 count issues
    rating_stmt = (
        select(SocialFeedback.rating, func.count(SocialFeedback.id))  # pylint: disable=not-callable
        .where(getattr(SocialFeedback, column_name) == target_id, SocialFeedback.rating.isnot(None))
        .group_by(SocialFeedback.rating)
    )
    rating_counts_res = db.session.execute(rating_stmt).all()

    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_rating_sum = 0
    total_rating_count = 0

    for rating, count in rating_counts_res:
        if rating in rating_counts:
            rating_counts[rating] = count
            total_rating_sum += rating * count
            total_rating_count += count

    average_rating = 0.0
    if total_rating_count > 0:
        average_rating = round(total_rating_sum / total_rating_count, 2)

    return jsonify(
        {
            "success": True,
            "data": {
                "feedbacks": [f.to_dict() for f in feedbacks],
                "stats": {
                    "average_rating": average_rating,
                    "total_count": len(feedbacks),
                    "total_ratings": total_rating_count,
                    "rating_counts": rating_counts,
                },
            },
        }
    )


def _validate_feedback_data(data: dict | None) -> tuple[int | None, str | None, str | None]:
    """Validate rating and comment in request data, returning (rating, comment, error_message)."""
    if not isinstance(data, dict):
        return None, None, "Invalid JSON payload"

    rating = data.get("rating")
    comment = data.get("comment")

    if rating is not None:
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return None, None, "Rating must be between 1 and 5"
        except (ValueError, TypeError):
            return None, None, "Rating must be a valid integer between 1 and 5"

    if comment is not None:
        comment = _sanitize_text(str(comment))
        if len(comment) > MAX_SOCIAL_TEXT_LENGTH:
            return None, None, f"Comment must be at most {MAX_SOCIAL_TEXT_LENGTH} characters"

    return rating, comment, None


@api_bp.route("/feedback/<string:level>/<int:target_id>", methods=["POST"])
@require_auth
def upsert_social_feedback(level: str, target_id: int) -> Response | tuple[Response, int]:
    """
    Create or update social feedback (rating and/or comment) for the authenticated user.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {list(VALID_LEVELS)}", "code": 400}), 400

    if not _verify_target_exists(level, target_id):
        return jsonify({"error": f"{level.capitalize()} not found", "code": 404}), 404

    data = request.get_json(silent=True)
    rating, comment, error_msg = _validate_feedback_data(data)
    if error_msg:
        return jsonify({"error": error_msg, "code": 400}), 400

    # Find existing feedback
    column_name = f"{level}_id"
    stmt = select(SocialFeedback).where(SocialFeedback.user_id == user_id, getattr(SocialFeedback, column_name) == target_id)
    feedback = db.session.execute(stmt).scalar_one_or_none()

    if feedback:
        if rating is not None:
            feedback.rating = rating
        if comment is not None:
            feedback.comment = comment
        feedback.updated_at = datetime.now(UTC)
    else:
        # Create new feedback record with exactly one foreign key set
        kwargs = {"user_id": user_id, "rating": rating, "comment": comment, column_name: target_id}
        feedback = SocialFeedback(**kwargs)
        db.session.add(feedback)

    db.session.commit()
    return jsonify({"success": True, "data": feedback.to_dict()})


@api_bp.route("/feedback/<string:level>/<int:target_id>", methods=["DELETE"])
@require_auth
def delete_social_feedback(level: str, target_id: int) -> Response | tuple[Response, int]:
    """
    Delete the social feedback (rating and comment) for the authenticated user.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {list(VALID_LEVELS)}", "code": 400}), 400

    column_name = f"{level}_id"
    stmt = select(SocialFeedback).where(SocialFeedback.user_id == user_id, getattr(SocialFeedback, column_name) == target_id)
    feedback = db.session.execute(stmt).scalar_one_or_none()

    if not feedback:
        return jsonify({"error": "Feedback not found", "code": 404}), 404

    db.session.delete(feedback)
    db.session.commit()

    return jsonify({"success": True, "message": "Feedback deleted successfully"})


@api_bp.route("/notes/<string:level>/<int:target_id>", methods=["GET"])
def get_social_notes(level: str, target_id: int) -> Response | tuple[Response, int]:
    """
    Get all social notes/comments for a specific FRBR level and resource ID.
    Notes are returned chronologically (newest first).
    """
    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {list(VALID_LEVELS)}", "code": 400}), 400

    if not _verify_target_exists(level, target_id):
        return jsonify({"error": f"{level.capitalize()} not found", "code": 404}), 404

    column_name = f"{level}_id"
    stmt = select(SocialNote).where(getattr(SocialNote, column_name) == target_id).order_by(SocialNote.created_at.desc())
    notes = db.session.execute(stmt).scalars().all()

    return jsonify(
        {
            "success": True,
            "data": [note.to_dict() for note in notes],
        }
    )


@api_bp.route("/notes/<string:level>/<int:target_id>", methods=["POST"])
@require_auth
def create_social_note(level: str, target_id: int) -> Response | tuple[Response, int]:
    """
    Add a new personal note or comment for a specific FRBR level and resource ID.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {list(VALID_LEVELS)}", "code": 400}), 400

    if not _verify_target_exists(level, target_id):
        return jsonify({"error": f"{level.capitalize()} not found", "code": 404}), 404

    data = request.get_json(silent=True)
    note_text, error_msg = _validate_note_input(data)
    if error_msg:
        return jsonify({"error": error_msg, "code": 400}), 400

    column_name = f"{level}_id"
    kwargs = {"user_id": user_id, "note": note_text, column_name: target_id}
    new_note = SocialNote(**kwargs)
    db.session.add(new_note)
    db.session.commit()

    return jsonify({"success": True, "data": new_note.to_dict()}), 201


@api_bp.route("/notes/<int:note_id>", methods=["PUT"])
@require_auth
def update_social_note(note_id: int) -> Response | tuple[Response, int]:
    """
    Update the text of a user's personal note or comment.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    note = db.session.get(SocialNote, note_id)
    if not note:
        return jsonify({"error": "Note not found", "code": 404}), 404

    if str(note.user_id) != str(user_id):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    data = request.get_json(silent=True)
    note_text, error_msg = _validate_note_input(data)
    if error_msg:
        return jsonify({"error": error_msg, "code": 400}), 400

    note.note = note_text
    note.updated_at = datetime.now(UTC)
    db.session.commit()

    return jsonify({"success": True, "data": note.to_dict()})


@api_bp.route("/notes/<int:note_id>", methods=["DELETE"])
@require_auth
def delete_social_note(note_id: int) -> Response | tuple[Response, int]:
    """
    Delete a user's personal note or comment.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    note = db.session.get(SocialNote, note_id)
    if not note:
        return jsonify({"error": "Note not found", "code": 404}), 404

    if str(note.user_id) != str(user_id):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    db.session.delete(note)
    db.session.commit()

    return jsonify({"success": True, "message": "Note deleted successfully"})


def _validate_escalation_input(data: dict | None) -> tuple[dict | None, str | None]:
    """Validate escalation request input data, returning (validated_dict, error_message)."""
    if not data:
        return None, "Missing JSON payload"

    field_name = _sanitize_text(str(data.get("field_name", "")))
    suggested_value = _sanitize_text(str(data.get("suggested_value", "")))

    if not field_name:
        return None, "field_name is required"
    if not suggested_value:
        return None, "suggested_value is required"

    current_val_raw = data.get("current_value")
    current_value = _sanitize_text(str(current_val_raw)) if current_val_raw is not None else None

    note_raw = data.get("note")
    note = _sanitize_text(str(note_raw)) if note_raw is not None else None

    for val, name in [(suggested_value, "suggested_value"), (current_value, "current_value"), (note, "note")]:
        if val and len(val) > MAX_SOCIAL_TEXT_LENGTH:
            return None, f"{name} must be at most {MAX_SOCIAL_TEXT_LENGTH} characters"

    return {
        "field_name": field_name,
        "suggested_value": suggested_value,
        "current_value": current_value,
        "note": note,
    }, None


@api_bp.route("/escalations/<level>/<int:target_id>", methods=["POST"])
@require_auth
@require_permission(PermissionName.ESCALATE_REQUEST)
def create_escalation_request(level: str, target_id: int) -> Response | tuple[Response, int]:
    """Submit a custodian escalation request targeting a FRBR entity field."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    if level not in VALID_LEVELS:
        return jsonify({"error": f"Invalid level: '{level}'", "code": 400}), 400

    if not _verify_target_exists(level, target_id):
        return jsonify({"error": f"{level.capitalize()} not found", "code": 404}), 404

    data = request.get_json(silent=True)
    validated, error_msg = _validate_escalation_input(data)
    if error_msg or not validated:
        return jsonify({"error": error_msg or "Invalid input", "code": 400}), 400

    kwargs = {
        "user_id": user_id,
        "field_name": validated["field_name"],
        "suggested_value": validated["suggested_value"],
        "current_value": validated["current_value"],
        "note": validated["note"],
        "status": "pending",
        f"{level}_id": target_id,
    }

    escalation = EscalationRequest(**kwargs)
    db.session.add(escalation)
    db.session.commit()

    return jsonify({"success": True, "data": escalation.to_dict()}), 201


@api_bp.route("/escalations/mine", methods=["GET"])
@require_auth
def list_my_escalation_requests() -> Response | tuple[Response, int]:
    """List escalation requests submitted by the current user."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    stmt = select(EscalationRequest).where(EscalationRequest.user_id == user_id).order_by(EscalationRequest.created_at.desc())
    requests = db.session.scalars(stmt).all()
    return jsonify({"success": True, "data": [req.to_dict() for req in requests]})


@api_bp.route("/escalations/queue", methods=["GET"])
@require_auth
@require_permission(PermissionName.ESCALATE_RESOLVE)
def list_escalation_queue() -> Response | tuple[Response, int]:
    """List escalation requests for custodian review.

    Supports optional ``?status=`` query parameter (comma-separated list of
    statuses). Defaults to ``pending`` when absent, preserving backward
    compatibility.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    raw_status = request.args.get("status", "pending")
    statuses = [s.strip().lower() for s in raw_status.split(",") if s.strip()]

    allowed_statuses = {"pending", "accepted", "rejected", "duplicate"}
    for s in statuses:
        if s not in allowed_statuses:
            return jsonify(
                {"error": f"Invalid status '{s}'. Must be one of {sorted(allowed_statuses)}", "code": 400}
            ), 400

    stmt = (
        select(EscalationRequest)
        .options(selectinload(EscalationRequest.user))  # type: ignore[arg-type]
        .where(EscalationRequest.status.in_(statuses))
        .order_by(EscalationRequest.created_at.desc())
    )
    requests = db.session.scalars(stmt).all()
    return jsonify({"success": True, "data": [req.to_dict() for req in requests]})


@api_bp.route("/escalations/<int:escalation_id>", methods=["PATCH"])
@require_auth
@require_permission(PermissionName.ESCALATE_RESOLVE)
def resolve_escalation_request(escalation_id: int) -> Response | tuple[Response, int]:
    """Resolve an escalation request (status: accepted, rejected, duplicate)."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    escalation = db.session.get(EscalationRequest, escalation_id)
    if not escalation:
        return jsonify({"error": "Escalation request not found", "code": 404}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    valid_statuses = {"accepted", "rejected", "duplicate"}
    if not new_status or new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of {sorted(valid_statuses)}", "code": 400}), 400

    resolution_note = data.get("resolution_note")
    if resolution_note is not None:
        resolution_note = _sanitize_text(str(resolution_note))
        if len(resolution_note) > MAX_SOCIAL_TEXT_LENGTH:
            return jsonify({"error": f"resolution_note must be at most {MAX_SOCIAL_TEXT_LENGTH} characters", "code": 400}), 400

    escalation.status = new_status
    escalation.resolved_by = user_id
    escalation.resolved_at = datetime.now(UTC)
    escalation.resolution_note = resolution_note
    db.session.commit()

    return jsonify({"success": True, "data": escalation.to_dict()})
