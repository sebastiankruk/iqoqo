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
"""
API endpoints for the lending lifecycle:
  - Borrowers can request to loan an available item
  - Owners can list, approve, or reject pending requests
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.decorators import require_auth
from app.db.auth import User
from app.db.core import Item, ItemStatusLog
from app.db.lending import LoanRequest

logger = logging.getLogger(__name__)

lending_bp = Blueprint("lending", __name__, url_prefix="/api/lending")


@lending_bp.route("/items/<int:item_id>/loan-request", methods=["POST"])
@require_auth
def request_loan(item_id: int) -> Response | tuple[Response, int]:
    """Borrower submits a request to loan an available item from its owner."""
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"error": "Item not found", "code": 404}), 404

    # Validate borrowing constraints
    error_msg = None
    status_code = 400
    if str(item.owner_id) == str(user_id):
        error_msg = "Cannot request to loan your own item"
    elif item.collection_status != "available":
        error_msg = "Item is not available for lending"
    else:
        # Check for an already-pending request from this user
        stmt = select(LoanRequest).filter(
            LoanRequest.item_id == item_id,
            LoanRequest.requester_id == user_id,
            LoanRequest.status == "pending",
        )
        existing = db.session.scalars(stmt).first()
        if existing:
            error_msg = "A pending loan request already exists"
            status_code = 409

    if error_msg:
        return jsonify({"error": error_msg, "code": status_code}), status_code

    data = request.get_json() or {}
    loan_request = LoanRequest(
        item_id=item_id,
        requester_id=user_id,
        notes=data.get("notes"),
    )
    try:
        db.session.add(loan_request)
        db.session.commit()
        return jsonify({"success": True, "data": loan_request.to_dict()}), 201
    except SQLAlchemyError as e:
        logger.error("Error creating loan request: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@lending_bp.route("/requests", methods=["GET"])
@require_auth
def list_loan_requests() -> Response | tuple[Response, int]:
    """Owner or admin retrieves pending loan requests for their items."""
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    user = db.session.get(User, user_id)
    is_admin = user and any(role.name == "admin" for role in getattr(user, "roles", []))

    try:
        if is_admin:
            stmt = select(LoanRequest).order_by(LoanRequest.created_at.desc())
        else:
            # Only requests for items owned by this user
            stmt = (
                select(LoanRequest)
                .join(Item, LoanRequest.item_id == Item.id)
                .filter(Item.owner_id == user_id)
                .order_by(LoanRequest.created_at.desc())
            )

        requests_list = db.session.scalars(stmt).unique().all()
        return jsonify({"success": True, "data": [r.to_dict() for r in requests_list]}), 200
    except SQLAlchemyError as e:
        logger.error("Error listing loan requests: %s", e)
        return jsonify({"error": "Database error", "code": 500}), 500


@lending_bp.route("/requests/<int:request_id>", methods=["PATCH"])
@require_auth
def resolve_loan_request(request_id: int) -> Response | tuple[Response, int]:
    """Owner approves or rejects a pending loan request.

    On approval the item's ``collection_status`` is set to ``lent`` and a
    ``ItemStatusLog`` entry is written with ``new_status='lent'`` so that
    the FRBR timeline log shows "Loan approved by custodian".
    """
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    loan_request = db.session.get(LoanRequest, request_id)
    if not loan_request:
        return jsonify({"error": "Loan request not found", "code": 404}), 404

    item = db.session.get(Item, loan_request.item_id)
    if not item:
        return jsonify({"error": "Item not found", "code": 404}), 404

    # Validate action and authorization constraints
    error_msg = None
    status_code = 400
    user = db.session.get(User, user_id)
    is_admin = user and any(role.name == "admin" for role in getattr(user, "roles", []))
    action = None

    if str(item.owner_id) != str(user_id) and not is_admin:
        error_msg = "Forbidden"
        status_code = 403
    elif loan_request.status != "pending":
        error_msg = "Request is no longer pending"
    else:
        data = request.get_json() or {}
        action = data.get("action")
        if action not in ("approve", "reject"):
            error_msg = "action must be 'approve' or 'reject'"

    if error_msg:
        return jsonify({"error": error_msg, "code": status_code}), status_code

    try:
        loan_request.resolved_at = datetime.now(UTC)

        if action == "approve":
            loan_request.status = "approved"
            old_c_status = item.collection_status
            item.collection_status = "lent"
            item.lent_to_user_id = loan_request.requester_id

            # Write a timeline log entry that the E2E test checks for
            log = ItemStatusLog(
                item_id=item.id,
                user_id=user_id,
                old_status=old_c_status,
                new_status="lent",
            )
            db.session.add(log)
        else:
            loan_request.status = "rejected"

        db.session.commit()
        return jsonify({"success": True, "data": loan_request.to_dict()}), 200
    except SQLAlchemyError as e:
        logger.error("Error resolving loan request %s: %s", request_id, e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@lending_bp.route("/items/<int:item_id>/loan-status", methods=["GET"])
@require_auth
def get_loan_status(item_id: int) -> Response | tuple[Response, int]:
    """Returns the active loan request status for an item (from the borrower's perspective)."""
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    stmt = (
        select(LoanRequest)
        .filter(
            LoanRequest.item_id == item_id,
            LoanRequest.requester_id == user_id,
        )
        .order_by(LoanRequest.created_at.desc())
    )
    loan_request = db.session.scalars(stmt).first()

    if not loan_request:
        return jsonify({"success": True, "data": None}), 200

    return jsonify({"success": True, "data": loan_request.to_dict()}), 200


@lending_bp.route("/test/reset", methods=["POST"])
def reset_lending_test_state() -> Response | tuple[Response, int]:
    """E2E test helper: resets all lender items to available and deletes loan requests."""
    from flask import current_app

    if not current_app.config.get("TESTING"):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    from app.db.core import db

    try:
        # Reset lender items
        lender_items = Item.query.filter(Item.collection_status == "lent").all()
        for item in lender_items:
            item.collection_status = "available"
            item.lent_to_user_id = None
            db.session.add(item)
        # Delete stale loan requests
        LoanRequest.query.delete()
        db.session.commit()
        return jsonify({"success": True, "reset_count": len(lender_items)}), 200
    except SQLAlchemyError as e:
        logger.error("Error resetting lending test state: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500
