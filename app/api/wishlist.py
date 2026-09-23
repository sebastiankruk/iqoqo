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
"""Dedicated Wishlist API blueprint for UserWorkIntent CRUD.

This module provides a clean REST interface for managing wishlist entries
(UserWorkIntent) with positive integer IDs, fully separated from the physical
inventory /api/items endpoints. Supports FRBR F15/F16 binding via optional
expression_id and manifestation_id fields.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from flask import Blueprint, Response, g, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy.orm import joinedload

from app.api.core import invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth
from app.api.filters import parse_csv_param
from app.api.items import _extract_intent_media_info
from app.core.limiter import limiter
from app.db.models import (
    Expression,
    Manifestation,
    User,
    UserWorkIntent,
    Work,
    db,
)

logger = logging.getLogger(__name__)

wishlist_bp = Blueprint("wishlist", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Pydantic schemas for wishlist payload validation
# ---------------------------------------------------------------------------

class WishlistCreateSchema(BaseModel):
    """Payload for creating a new wishlist entry."""

    model_config = ConfigDict(extra="forbid")

    work_id: int = Field(..., gt=0, description="FRBR Work (F1) ID")
    expression_id: int | None = Field(default=None, gt=0, description="Optional FRBR Expression (F2) ID")
    manifestation_id: int | None = Field(default=None, gt=0, description="Optional FRBR Manifestation (F3) ID")
    status: str = Field(default="want_to_read", description="Progress status")
    is_hidden: bool = Field(default=False, description="Whether the entry is hidden from other users")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        from app.db.core import WORK_INTENT_STATUSES
        if v not in WORK_INTENT_STATUSES:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {WORK_INTENT_STATUSES}")
        return v

    @model_validator(mode="after")
    def check_manifestation_requires_expression(self) -> WishlistCreateSchema:
        if self.manifestation_id is not None and self.expression_id is None:
            raise ValueError("manifestation_id requires expression_id to be set")
        return self


class WishlistUpdateSchema(BaseModel):
    """Payload for updating an existing wishlist entry."""

    model_config = ConfigDict(extra="forbid")

    expression_id: int | None = Field(default=None, gt=0, description="Optional FRBR Expression (F2) ID")
    manifestation_id: int | None = Field(default=None, gt=0, description="Optional FRBR Manifestation (F3) ID")
    status: str | None = Field(default=None, description="Progress status")
    is_hidden: bool | None = Field(default=None, description="Whether the entry is hidden from other users")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        from app.db.core import WORK_INTENT_STATUSES
        if v not in WORK_INTENT_STATUSES:
            raise ValueError(f"Invalid status: '{v}'. Must be one of {WORK_INTENT_STATUSES}")
        return v


# ---------------------------------------------------------------------------
# FRBR hierarchy validation
# ---------------------------------------------------------------------------

def _validate_frbr_hierarchy(
    work_id: int,
    expression_id: int | None,
    manifestation_id: int | None,
) -> str | None:
    """Validate FRBR hierarchy consistency for wishlist binding.

    Ensures:
    - expression_id (if set) belongs to work_id
    - manifestation_id (if set) belongs to expression_id (if set) or to an
      expression of work_id

    Returns an error message string on failure, or None on success.
    Supports F15 Complex Works and F16 Container Works: a manifestation
    may belong to any expression in the work's expression tree.
    """
    if expression_id is not None:
        expression = db.session.get(Expression, expression_id)
        if not expression:
            return "Invalid field for wishlist entry"
        if expression.work_id != work_id:
            if not _is_expression_in_work_tree(expression, work_id):
                return "Invalid field for wishlist entry"

    if manifestation_id is not None:
        manifestation = db.session.get(Manifestation, manifestation_id)
        if not manifestation:
            return "Invalid field for wishlist entry"
        manif_expr_id = manifestation.expression_id
        if expression_id is not None:
            if manif_expr_id != expression_id:
                return "Invalid field for wishlist entry"
        else:
            manif_expr = db.session.get(Expression, manif_expr_id) if manif_expr_id else None
            if not manif_expr or manif_expr.work_id != work_id:
                if not (manif_expr and _is_expression_in_work_tree(manif_expr, work_id)):
                    return "Invalid field for wishlist entry"

    return None


def _is_expression_in_work_tree(expression: Expression, work_id: int) -> bool:
    """Check if expression belongs to work_id directly or via F15/F16 work links."""
    if expression.work_id == work_id:
        return True
    expr_work = expression.work
    if expr_work and expr_work.member_of:
        for part_link in expr_work.member_of:
            if part_link.container_work_id == work_id:
                return True
    return False


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_intent(intent: UserWorkIntent, user_id: uuid.UUID | None) -> dict[str, Any]:
    """Serialize a UserWorkIntent to a rich FRBR-aware dictionary."""
    work = intent.work
    manifestation = intent.manifestation
    expression = intent.expression

    # Resolve primary expression and manifestation if not directly bound
    primary_expr = expression
    if not manifestation and work:
        for expr in work.expressions:
            if expr.manifestations:
                manifestation = expr.manifestations[0]
                primary_expr = expr
                break
    if primary_expr is None and work and work.expressions:
        primary_expr = work.expressions[0]

    work_type, medium_type = _extract_intent_media_info(work, primary_expr, manifestation)

    _cover_url = None
    _cover_status = None
    if manifestation:
        _cover_url = manifestation.cover_url or (manifestation.meta.get("cover_url") if manifestation.meta else None)
        _cover_status = manifestation.meta.get("cover_status") if manifestation.meta else None

    data: dict[str, Any] = {
        "id": intent.id,
        "work_id": intent.work_id,
        "expression_id": intent.expression_id,
        "manifestation_id": intent.manifestation_id or (manifestation.id if manifestation else None),
        "owner_id": str(intent.user_id),
        "status": intent.status,
        "collection_status": "wish_list",
        "is_hidden": intent.is_hidden,
        "title": work.title if work else None,
        "authors": work.meta.get("authors", []) if work and work.meta else [],
        "isbn": manifestation.isbn13 if manifestation else None,
        "publisher": manifestation.publisher if manifestation else None,
        "cover_url": _cover_url,
        "cover_status": _cover_status,
        "content_type": primary_expr.content_type if primary_expr else None,
        "work_type": work_type,
        "medium_type": medium_type,
        "is_owner": intent.user_id == user_id if user_id else False,
        "tags": [],
        "added_at": intent.created_at.isoformat() if hasattr(intent.created_at, "isoformat") else intent.created_at,
        "updated_at": (
            (intent.updated_at or intent.created_at).isoformat()
            if hasattr((intent.updated_at or intent.created_at), "isoformat")
            else (intent.updated_at or intent.created_at)
        ),
    }

    if primary_expr:
        data["expression"] = {
            "id": primary_expr.id,
            "content_type": primary_expr.content_type,
            "language": primary_expr.language,
            "kind": primary_expr.kind,
        }
    if work:
        container_work_id = work.member_of[0].container_work_id if work.member_of else None
        data["work"] = {
            "id": work.id,
            "title": work.title,
            "authors": work.meta.get("authors", []) if work.meta else [],
            "meta": work.meta,
            "container_work_id": container_work_id,
        }
    if manifestation:
        data["manifestation_meta"] = manifestation.meta

    return data


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@wishlist_bp.route("/wishlist", methods=["GET"])
@limiter.limit("120 per minute", override_defaults=True)
@optional_auth
def get_wishlist() -> Response | tuple[Response, int]:
    """List the authenticated user's wishlist entries with pagination and filters."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": [], "error": "Unauthorized"}), 401

    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    statuses_filter = request.args.get("statuses", request.args.get("status", None))
    work_type_filter = request.args.get("work_type", None)
    medium_type_filter = request.args.get("medium_type", None)
    q = request.args.get("q", request.args.get("search", "")).strip()

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * limit

    query = (
        db.session.query(UserWorkIntent)
        .options(
            joinedload(UserWorkIntent.work)
            .selectinload(Work.expressions)
            .selectinload(Expression.manifestations)
        )
        .options(joinedload(UserWorkIntent.expression))
        .options(joinedload(UserWorkIntent.manifestation))
        .filter(UserWorkIntent.user_id == user_id)
    )

    if statuses_filter:
        statuses_list = parse_csv_param(statuses_filter) or []
        _INTENT_LEVEL_STATUSES = {"want_to_read", "want_to_listen", "want_to_watch", "want_to_play"}
        intent_statuses = [s for s in statuses_list if s in _INTENT_LEVEL_STATUSES]
        if intent_statuses:
            query = query.filter(UserWorkIntent.status.in_(intent_statuses))
        elif "wish_list" in statuses_list:
            query = query.filter(UserWorkIntent.status != "fulfilled")
        else:
            query = query.filter(UserWorkIntent.status != "fulfilled")
    else:
        query = query.filter(UserWorkIntent.status != "fulfilled")

    if q:
        escaped_q = q.strip().lower().replace("%", r"\%").replace("_", r"\_")
        pattern = f"%{escaped_q}%"
        query = query.join(Work, UserWorkIntent.work_id == Work.id).filter(
            db.or_(
                Work.title.ilike(pattern, escape="\\"),
                db.cast(Work.meta["authors"], db.String).ilike(pattern, escape="\\"),
            )
        )

    # Pre-filter for work_type and medium_type (applied post-serialization)
    all_intents = query.order_by(UserWorkIntent.updated_at.desc().nullslast(), UserWorkIntent.id.desc()).all()

    data = []
    for intent in all_intents:
        serialized = _serialize_intent(intent, user_id)

        if work_type_filter and serialized.get("work_type") != work_type_filter:
            continue
        if medium_type_filter and serialized.get("medium_type") != medium_type_filter:
            continue

        data.append(serialized)

    total = len(data)
    paginated = data[offset:offset + limit]

    return jsonify({
        "success": True,
        "data": paginated,
        "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
        "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total},
        "error": None,
    })


@wishlist_bp.route("/wishlist", methods=["POST"])
@limiter.limit("30 per minute", override_defaults=True)
@require_auth
def create_wishlist_item() -> Response | tuple[Response, int]:
    """Create a new wishlist entry (UserWorkIntent)."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    try:
        payload = WishlistCreateSchema(**data)
    except ValidationError as e:
        return jsonify({"error": f"Invalid payload: {e}", "code": 400}), 400

    # Verify work exists
    work = db.session.get(Work, payload.work_id)
    if not work:
        return jsonify({"success": False, "data": None, "error": "Invalid field for wishlist entry"}), 404

    # Validate FRBR hierarchy
    hierarchy_err = _validate_frbr_hierarchy(payload.work_id, payload.expression_id, payload.manifestation_id)
    if hierarchy_err:
        return jsonify({"success": False, "data": None, "error": hierarchy_err}), 400

    # Check for duplicate
    existing_query = UserWorkIntent.query.filter_by(
        user_id=user_id,
        work_id=payload.work_id,
    )
    if payload.expression_id is not None:
        existing_query = existing_query.filter_by(expression_id=payload.expression_id)
    else:
        existing_query = existing_query.filter(UserWorkIntent.expression_id.is_(None))

    if payload.manifestation_id is not None:
        existing_query = existing_query.filter_by(manifestation_id=payload.manifestation_id)
    else:
        existing_query = existing_query.filter(UserWorkIntent.manifestation_id.is_(None))

    existing = existing_query.first()
    if existing:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry already exists for this target"}), 409

    intent = UserWorkIntent(
        user_id=user_id,
        work_id=payload.work_id,
        expression_id=payload.expression_id,
        manifestation_id=payload.manifestation_id,
        status=payload.status,
        is_hidden=payload.is_hidden,
    )
    db.session.add(intent)

    try:
        db.session.commit()
        serialized = _serialize_intent(intent, user_id)
        return jsonify({"success": True, "data": serialized, "error": None}), 201
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        logger.exception("Failed to create wishlist item for user %s: %s", user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create wishlist entry"}), 500


@wishlist_bp.route("/wishlist/<int:intent_id>", methods=["GET"])
@limiter.limit("120 per minute", override_defaults=True)
@optional_auth
def get_wishlist_item(intent_id: int) -> Response | tuple[Response, int]:
    """Get a single wishlist entry by ID."""
    user_id = getattr(g, "user_id", None)

    if user_id is None:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    intent = (
        db.session.query(UserWorkIntent)
        .options(
            joinedload(UserWorkIntent.work)
            .selectinload(Work.expressions)
            .selectinload(Expression.manifestations)
        )
        .options(joinedload(UserWorkIntent.expression))
        .options(joinedload(UserWorkIntent.manifestation))
        .filter(UserWorkIntent.id == intent_id)
        .first()
    )

    if not intent:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    is_owner = intent.user_id == user_id
    user = db.session.get(User, user_id)
    is_admin = bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))

    if not (is_owner or is_admin) and intent.is_hidden:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    # BOLA protection: non-owners accessing non-hidden entries still get 404
    # to prevent enumeration
    if not is_owner and not is_admin:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    serialized = _serialize_intent(intent, user_id)
    return jsonify({"success": True, "data": serialized, "error": None})


@wishlist_bp.route("/wishlist/<int:intent_id>", methods=["PUT"])
@limiter.limit("60 per minute", override_defaults=True)
@require_auth
def update_wishlist_item(intent_id: int) -> Response | tuple[Response, int]:
    """Update an existing wishlist entry."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    intent = UserWorkIntent.query.filter_by(id=intent_id).with_for_update().first()
    if not intent:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    is_owner = intent.user_id == user_id
    user = db.session.get(User, user_id)
    is_admin = bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))

    # BOLA protection: return 404 for non-owners
    if not (is_owner or is_admin):
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    try:
        payload = WishlistUpdateSchema(**data)
    except ValidationError as e:
        return jsonify({"error": f"Invalid payload: {e}", "code": 400}), 400

    # Determine new FRBR binding values (use existing if not being updated)
    new_expression_id = payload.expression_id if payload.expression_id is not None else intent.expression_id
    new_manifestation_id = payload.manifestation_id if payload.manifestation_id is not None else intent.manifestation_id

    # Validate FRBR hierarchy if binding is changing
    if (
        (payload.expression_id is not None and payload.expression_id != intent.expression_id)
        or (payload.manifestation_id is not None and payload.manifestation_id != intent.manifestation_id)
    ):
        hierarchy_err = _validate_frbr_hierarchy(intent.work_id, new_expression_id, new_manifestation_id)
        if hierarchy_err:
            return jsonify({"success": False, "data": None, "error": hierarchy_err}), 400

    if payload.expression_id is not None:
        intent.expression_id = payload.expression_id
    if payload.manifestation_id is not None:
        intent.manifestation_id = payload.manifestation_id
    if payload.status is not None:
        intent.status = payload.status
    if payload.is_hidden is not None:
        intent.is_hidden = payload.is_hidden

    try:
        db.session.commit()
        serialized = _serialize_intent(intent, user_id)
        return jsonify({"success": True, "data": serialized, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        logger.exception("Failed to update wishlist item %s: %s", intent_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to update wishlist entry"}), 500


@wishlist_bp.route("/wishlist/<int:intent_id>", methods=["DELETE"])
@limiter.limit("30 per minute", override_defaults=True)
@require_auth
def delete_wishlist_item(intent_id: int) -> Response | tuple[Response, int]:
    """Delete a wishlist entry."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    intent = UserWorkIntent.query.filter_by(id=intent_id).first()
    if not intent:
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    is_owner = intent.user_id == user_id
    user = db.session.get(User, user_id)
    is_admin = bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))

    # BOLA protection: return 404 for non-owners
    if not (is_owner or is_admin):
        return jsonify({"success": False, "data": None, "error": "Wishlist entry not found"}), 404

    try:
        db.session.delete(intent)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": intent_id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        logger.exception("Failed to delete wishlist item %s: %s", intent_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to delete wishlist entry"}), 500
