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

import json
import logging
from datetime import UTC, datetime
from typing import Any

import bleach
from flask import Response, g, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.api.core import api_bp
from app.api.decorators import optional_auth, require_auth, require_permission
from app.core.frbr_service import update_frbr_entity_type
from app.core.permissions import PermissionName
from app.db.models import EscalationRequest, Expression, Item, Manifestation, SocialFeedback, SocialNote, User, Work, db

logger = logging.getLogger(__name__)

VALID_LEVELS = {"work", "expression", "manifestation", "item"}

# Defense-in-depth ceiling for free-text social content. Notes/comments are
# rendered as plain text on the frontend (no dangerouslySetInnerHTML), but we
# still cap length (storage/DoS hardening) and strip markup at ingress in case
# a future rendering path relaxes that assumption.
MAX_SOCIAL_TEXT_LENGTH = 2048


def _sanitize_text(value: str) -> str:
    """Strip HTML markup from free-text user input using bleach (defense in depth)."""
    cleaned: str = str(bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True)).strip()
    return cleaned


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


def _resolve_target_entity(escalation: EscalationRequest) -> dict[str, Any] | None:
    """Build a target_entity dict for an escalation request."""
    if escalation.work_id is not None:
        entity = db.session.get(Work, escalation.work_id)
        if entity is not None:
            return {
                "id": entity.id,
                "title": entity.title,
                "type": "Work",
                "current_state": (entity.meta or {}).get("type") or "work",
            }
    if escalation.expression_id is not None:
        entity = db.session.get(Expression, escalation.expression_id)
        if entity is not None:
            return {
                "id": entity.id,
                "title": entity.work.title if entity.work else f"Expression {entity.id}",
                "type": "Expression",
                "current_state": entity.kind or entity.content_type or "expression",
            }
    if escalation.manifestation_id is not None:
        entity = db.session.get(Manifestation, escalation.manifestation_id)
        if entity is not None:
            return {
                "id": entity.id,
                "title": entity.title,
                "type": "Manifestation",
                "current_state": entity.format or (entity.meta or {}).get("format") or "manifestation",
            }
    if escalation.item_id is not None:
        entity = db.session.get(Item, escalation.item_id)
        if entity is not None:
            return {
                "id": entity.id,
                "title": entity.title if hasattr(entity, "title") and entity.title else f"Item {entity.id}",
                "type": "Item",
                "current_state": entity.status,
            }
    if escalation.request_type == "new_media_type":
        title = "New Media Type"
        category = "custom"
        if escalation.suggested_value:
            try:
                payload = json.loads(escalation.suggested_value)
                title = payload.get("proposed_format") or title
                category = payload.get("proposed_category") or category
            except Exception:
                title = escalation.suggested_value or title
        return {
            "id": None,
            "title": title,
            "type": "NewMediaType",
            "current_state": category,
        }
    return None


@api_bp.route("/feedback/<string:level>/<int:target_id>", methods=["GET"])
@optional_auth
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
@optional_auth
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

    request_type = str(data.get("request_type", "correction")).strip().lower()
    if request_type not in {"correction", "deletion", "change_type"}:
        return None, f"Invalid request_type '{request_type}'. Must be 'correction', 'deletion' or 'change_type'"

    note_raw = data.get("note")
    note = _sanitize_text(str(note_raw)) if note_raw is not None else None

    error: str | None = None
    field_name = ""
    suggested_value = ""
    current_value = None

    if request_type == "deletion":
        if not note:
            error = "Note is required for deletion requests"
    else:
        field_name = _sanitize_text(str(data.get("field_name", "")))
        suggested_value = _sanitize_text(str(data.get("suggested_value", "")))
        current_val_raw = data.get("current_value")
        current_value = _sanitize_text(str(current_val_raw)) if current_val_raw is not None else None

        if not field_name:
            error = "field_name is required"
        elif not suggested_value:
            error = "suggested_value is required"

    if not error:
        for val, name in [(suggested_value, "suggested_value"), (current_value, "current_value"), (note, "note")]:
            if val and len(val) > MAX_SOCIAL_TEXT_LENGTH:
                error = f"{name} must be at most {MAX_SOCIAL_TEXT_LENGTH} characters"
                break

    if error:
        return None, error

    return {
        "request_type": request_type,
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
        "request_type": validated["request_type"],
        "target_type": level,
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


class NewMediaTypeEscalationPayload(BaseModel):
    """Schema for validating user proposals for new media types / physical formats."""

    model_config = ConfigDict(extra="ignore")

    proposed_category: str = Field(..., min_length=1, max_length=100)
    proposed_format: str = Field(..., min_length=1, max_length=100)
    parent_frbr_class: str = Field(default="F1_Work")
    sample_identifier_or_url: str | None = Field(default=None, max_length=500)
    suggested_properties: list[str] | None = None
    rationale: str = Field(..., min_length=1, max_length=MAX_SOCIAL_TEXT_LENGTH)

    @field_validator("proposed_category", "proposed_format", "rationale", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> str:
        if v is None:
            raise ValueError("Field cannot be null")
        cleaned = _sanitize_text(str(v))
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("sample_identifier_or_url", mode="before")
    @classmethod
    def sanitize_sample(cls, v: Any) -> str | None:
        if v is None or not str(v).strip():
            return None
        return _sanitize_text(str(v))

    @field_validator("parent_frbr_class")
    @classmethod
    def validate_frbr_class(cls, v: str) -> str:
        cleaned = v.strip()
        if cleaned not in {"F1_Work", "F16_Container_Work"}:
            raise ValueError("parent_frbr_class must be 'F1_Work' or 'F16_Container_Work'")
        return cleaned


def _notify_custodians_of_new_media_type(escalation: EscalationRequest, payload: dict[str, Any]) -> None:
    """Send in-app notification to all admins/custodians when a new media type proposal is submitted."""
    try:
        from app.core.notifications import create_notification
        from app.db.models import Role, User

        custodians = db.session.query(User).join(User.roles).filter(Role.name.in_(["admin", "custodian"])).distinct().all()
        for custodian in custodians:
            create_notification(
                user_id=custodian.id,
                notification_type="new_media_type_requested",
                payload={
                    "escalation_id": escalation.id,
                    "proposed_format": payload.get("proposed_format"),
                    "proposed_category": payload.get("proposed_category"),
                    "message": f"New media type proposed: {payload.get('proposed_format')}",
                },
                target_iri="/admin/content?tab=escalations",
            )
    except Exception as err:
        logger.warning("Failed to notify custodians of new media type escalation: %s", err)


@api_bp.route("/escalations", methods=["POST"])
@api_bp.route("/social/escalations", methods=["POST"])
@api_bp.route("/escalations/new-type", methods=["POST"])
@require_auth
@require_permission(PermissionName.ESCALATE_REQUEST)
def create_general_escalation_request() -> Response | tuple[Response, int]:
    """Submit a general escalation request not bound to an existing FRBR entity (e.g. new_media_type)."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    data = request.get_json(silent=True) or {}
    req_type = str(data.get("request_type", "")).strip().lower()

    if req_type != "new_media_type":
        return (
            jsonify(
                {
                    "error": "General escalation must specify request_type='new_media_type'. For entity escalations, use /api/escalations/<level>/<target_id>",
                    "code": 400,
                }
            ),
            400,
        )

    try:
        validated = NewMediaTypeEscalationPayload.model_validate(data)
    except ValidationError as e:
        first_err = e.errors()[0]
        field = ".".join(str(loc) for loc in first_err.get("loc", []))
        msg = first_err.get("msg", "Validation error")
        return jsonify({"error": f"{field}: {msg}" if field else msg, "code": 400}), 400

    payload_dict = validated.model_dump()
    kwargs = {
        "user_id": user_id,
        "request_type": "new_media_type",
        "target_type": "new_media_type",
        "field_name": "new_media_type",
        "current_value": None,
        "suggested_value": json.dumps(payload_dict),
        "note": validated.rationale,
        "status": "pending",
    }
    escalation = EscalationRequest(**kwargs)
    db.session.add(escalation)
    db.session.commit()

    _notify_custodians_of_new_media_type(escalation, payload_dict)

    return jsonify({"success": True, "data": {**escalation.to_dict(), "target_entity": _resolve_target_entity(escalation)}}), 201


@api_bp.route("/escalations/mine", methods=["GET"])
@require_auth
def list_my_escalation_requests() -> Response | tuple[Response, int]:
    """List escalation requests submitted by the current user."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    stmt = (
        select(EscalationRequest)
        .options(
            selectinload(EscalationRequest.work),  # type: ignore[arg-type]
            selectinload(EscalationRequest.expression),  # type: ignore[arg-type]
            selectinload(EscalationRequest.manifestation),  # type: ignore[arg-type]
            selectinload(EscalationRequest.item),  # type: ignore[arg-type]
        )
        .where(EscalationRequest.user_id == user_id)
        .order_by(EscalationRequest.created_at.desc())
    )
    requests = db.session.scalars(stmt).all()
    return jsonify(
        {
            "success": True,
            "data": [{**req.to_dict(), "target_entity": _resolve_target_entity(req)} for req in requests],
        }
    )


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
            return jsonify({"error": f"Invalid status '{s}'. Must be one of {sorted(allowed_statuses)}", "code": 400}), 400

    stmt = (
        select(EscalationRequest)
        .options(
            selectinload(EscalationRequest.user),  # type: ignore[arg-type]
            selectinload(EscalationRequest.resolver),  # type: ignore[arg-type]
            selectinload(EscalationRequest.work),  # type: ignore[arg-type]
            selectinload(EscalationRequest.expression),  # type: ignore[arg-type]
            selectinload(EscalationRequest.manifestation),  # type: ignore[arg-type]
            selectinload(EscalationRequest.item),  # type: ignore[arg-type]
        )
        .where(EscalationRequest.status.in_(statuses))
        .order_by(EscalationRequest.created_at.desc())
    )
    requests = db.session.scalars(stmt).all()
    return jsonify(
        {
            "success": True,
            "data": [{**req.to_dict(), "target_entity": _resolve_target_entity(req)} for req in requests],
        }
    )


@api_bp.route("/escalations/<int:escalation_id>", methods=["GET"])
@require_auth
@require_permission(PermissionName.ESCALATE_RESOLVE)
def get_escalation_request(escalation_id: int) -> Response | tuple[Response, int]:
    """Fetch a single escalation request with enriched target entity details."""
    stmt = (
        select(EscalationRequest)
        .options(
            selectinload(EscalationRequest.user),  # type: ignore[arg-type]
            selectinload(EscalationRequest.resolver),  # type: ignore[arg-type]
            selectinload(EscalationRequest.work),  # type: ignore[arg-type]
            selectinload(EscalationRequest.expression),  # type: ignore[arg-type]
            selectinload(EscalationRequest.manifestation),  # type: ignore[arg-type]
            selectinload(EscalationRequest.item),  # type: ignore[arg-type]
        )
        .where(EscalationRequest.id == escalation_id)
    )
    escalation = db.session.execute(stmt).scalar_one_or_none()
    if escalation is None:
        return jsonify({"error": "Escalation request not found", "code": 404}), 404

    data = escalation.to_dict()
    data["target_entity"] = _resolve_target_entity(escalation)
    return jsonify({"success": True, "data": data})


def _delete_manifestation_target(escalation: EscalationRequest, user: User | None) -> tuple[Response, int] | None:
    """Handle manifestation deletion when accepting a deletion request."""
    if not user or not user.has_permission(PermissionName.DELETE_MANIFESTATION):
        return jsonify({"error": "Permission delete:manifestation required to accept deletion request", "code": 403}), 403
    if not escalation.manifestation_id:
        return jsonify({"error": "Target entity no longer exists", "code": 404}), 404

    manif_stmt = select(Manifestation).where(Manifestation.id == escalation.manifestation_id).with_for_update()
    target_manif = db.session.execute(manif_stmt).scalar_one_or_none()
    if not target_manif:
        return jsonify({"error": "Target entity no longer exists", "code": 404}), 404

    cnt = func.count()  # pylint: disable=not-callable
    item_count = db.session.execute(select(cnt).select_from(Item).where(Item.manifestation_id == escalation.manifestation_id)).scalar() or 0
    if item_count > 0:
        db.session.rollback()
        return jsonify({"error": "Cannot delete manifestation: dependent items exist", "code": 409}), 409

    from app.db.models import ScanTelemetry

    ScanTelemetry.query.filter_by(manifestation_id=escalation.manifestation_id).update(
        {"manifestation_id": None}, synchronize_session=False
    )
    db.session.delete(target_manif)
    return None


def _delete_item_target(escalation: EscalationRequest, user: User | None, user_id: Any) -> tuple[Response, int] | None:
    """Handle item deletion when accepting a deletion request."""
    if not user or not user.has_permission(PermissionName.DELETE_ITEM):
        return jsonify({"error": "Permission delete:item required to accept deletion request", "code": 403}), 403
    if not escalation.item_id:
        return jsonify({"error": "Target entity no longer exists", "code": 404}), 404

    item_stmt = select(Item).where(Item.id == escalation.item_id).with_for_update()
    target_item = db.session.execute(item_stmt).scalar_one_or_none()
    if not target_item:
        return jsonify({"error": "Target entity no longer exists", "code": 404}), 404

    if target_item.owner_id != user_id:
        db.session.rollback()
        return jsonify({"error": "Forbidden: You do not own this item", "code": 403}), 403

    db.session.delete(target_item)
    return None


def _handle_deletion_acceptance(escalation: EscalationRequest, user: User | None, user_id: Any) -> tuple[Response, int] | None:
    """Helper to handle target entity deletion when accepting a deletion request."""
    target_level = escalation.target_type or ("manifestation" if escalation.manifestation_id else "item" if escalation.item_id else None)
    if target_level == "manifestation":
        return _delete_manifestation_target(escalation, user)
    if target_level == "item":
        return _delete_item_target(escalation, user, user_id)
    return None


def _validate_resolution_payload(data: dict) -> tuple[str | None, str | None, str | None]:
    """Validate resolution payload, returning (new_status, resolution_note, error_msg)."""
    new_status = data.get("status")
    valid_statuses = {"accepted", "rejected", "duplicate"}
    if not new_status or new_status not in valid_statuses:
        return None, None, f"Invalid status. Must be one of {sorted(valid_statuses)}"

    resolution_note = data.get("resolution_note")
    if resolution_note is not None:
        resolution_note = _sanitize_text(str(resolution_note))
        if len(resolution_note) > MAX_SOCIAL_TEXT_LENGTH:
            return None, None, f"resolution_note must be at most {MAX_SOCIAL_TEXT_LENGTH} characters"

    return str(new_status), resolution_note, None


def _handle_type_change_acceptance(
    escalation: EscalationRequest,
    requested_target_id: int | None = None,
) -> tuple[Response, int] | None:
    if escalation.manifestation_id:
        entity_class = Manifestation
        entity_id = escalation.manifestation_id
    elif escalation.expression_id:
        entity_class = Expression
        entity_id = escalation.expression_id
    elif escalation.work_id:
        entity_class = Work
        entity_id = escalation.work_id
    elif escalation.item_id:
        entity_class = Item
        entity_id = escalation.item_id
    else:
        return jsonify({"error": "No target entity for type change", "code": 400}), 400

    if requested_target_id is not None and requested_target_id != entity_id:
        return jsonify({"error": "Target entity ID in approval does not match escalation request", "code": 400}), 400

    try:
        update_frbr_entity_type(entity_class, entity_id, escalation.suggested_value)
    except ValueError as e:
        return jsonify({"error": str(e), "code": 400}), 400

    return None


@api_bp.route("/escalations/<int:escalation_id>", methods=["PATCH"])
@require_auth
@require_permission(PermissionName.ESCALATE_RESOLVE)
def resolve_escalation_request(escalation_id: int) -> Response | tuple[Response, int]:
    """Resolve an escalation request (status: accepted, rejected, duplicate)."""
    user_id = getattr(g, "user_id", None)
    data = request.get_json(silent=True) or {}
    new_status, resolution_note, err_msg = _validate_resolution_payload(data)
    if err_msg or not new_status:
        return jsonify({"error": err_msg, "code": 400}), 400

    user = db.session.get(User, user_id)

    try:
        stmt = select(EscalationRequest).where(EscalationRequest.id == escalation_id).with_for_update()
        escalation = db.session.execute(stmt).scalar_one_or_none()
        if not escalation:
            return jsonify({"error": "Escalation request not found", "code": 404}), 404

        requested_target_id = data.get("target_id")
        if requested_target_id is not None:
            try:
                requested_target_id = int(requested_target_id)
            except (TypeError, ValueError):
                return jsonify({"error": "target_id must be an integer", "code": 400}), 400

        err_resp = None
        if new_status == "accepted":
            if escalation.request_type == "deletion":
                err_resp = _handle_deletion_acceptance(escalation, user, user_id)
            elif escalation.request_type == "change_type":
                err_resp = _handle_type_change_acceptance(escalation, requested_target_id)

        if err_resp:
            return err_resp

        escalation.status = new_status
        escalation.resolved_by = user_id
        escalation.resolved_at = datetime.now(UTC)
        escalation.resolution_note = resolution_note
        resp_data = escalation.to_dict()
        db.session.commit()

        try:
            from app.core.notifications import create_notification

            if escalation.user_id:
                notif_type = "new_media_type_resolved" if escalation.request_type == "new_media_type" else "escalation_resolved"
                msg = (
                    f"Your new media type proposal #{escalation.id} was {new_status}"
                    if escalation.request_type == "new_media_type"
                    else f"Your escalation request #{escalation.id} was {new_status}"
                )
                create_notification(
                    user_id=escalation.user_id,
                    notification_type=notif_type,
                    payload={
                        "escalation_id": escalation.id,
                        "status": new_status,
                        "resolution_note": resolution_note,
                        "message": msg,
                    },
                    target_iri="/feedback?tab=my-escalations",
                )
        except Exception as notif_err:
            logger.warning("Failed to emit escalation resolution notification: %s", notif_err)

        return jsonify({"success": True, "data": resp_data})
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "Database error occurred during resolution", "code": 500}), 500
