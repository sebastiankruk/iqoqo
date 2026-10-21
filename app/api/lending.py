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

import hmac
import logging
import os
from datetime import UTC, datetime
from typing import Any

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.decorators import require_auth
from app.core.limiter import limiter
from app.db.auth import User
from app.db.core import Item, ItemStatusLog
from app.db.lending import LoanRequest

logger = logging.getLogger(__name__)

lending_bp = Blueprint("lending", __name__, url_prefix="/api/lending")


@lending_bp.route("/items/<int:item_id>/loan-request", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def request_loan(item_id: int) -> Response | tuple[Response, int]:
    """Borrower submits a request to loan an available item from its owner."""
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    # FRBR ontology boundary: virtual wishlist entries (id <= 0) cannot participate
    # in physical loan workflows. Only concrete, localized Items with positive IDs may be lent.
    if item_id <= 0:
        return (
            jsonify(
                {
                    "error": "Virtual items (id <= 0) cannot be lent. Only physical items with a positive ID are eligible for loan workflows.",
                    "code": 400,
                }
            ),
            400,
        )

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
        try:
            from app.core.notifications import create_notification

            target_owner_id = item.user_id or item.owner_id
            if target_owner_id:
                create_notification(
                    user_id=target_owner_id,
                    notification_type="loan_request",
                    payload={
                        "item_id": item.id,
                        "loan_request_id": loan_request.id,
                        "requester_id": str(user_id),
                        "message": f"Loan request received for item #{item.id}",
                    },
                    target_iri=f"/items/{item.id}",
                )
        except Exception as notif_err:
            logger.warning("Failed to emit local loan_request notification: %s", notif_err)

        return jsonify({"success": True, "data": loan_request.to_dict()}), 201
    except IntegrityError as e:
        db.session.rollback()
        original = e.orig
        diagnostic = getattr(original, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None) or getattr(original, "constraint_name", None)
        if constraint_name == "loan_requests_not_self_borrow":
            return jsonify({"error": "Cannot request to loan your own item", "code": 400}), 400
        logger.error("Integrity error creating loan request: %s", e)
        return jsonify({"error": "Database error", "code": 500}), 500
    except SQLAlchemyError as e:
        logger.error("Error creating loan request: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@lending_bp.route("/requests", methods=["GET"])
@limiter.limit("60 per minute")
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
@limiter.limit("30 per minute")
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

            # Record immutable ItemCustodyEvent
            from app.db.core import ItemCustodyEvent

            custody_event = ItemCustodyEvent(
                item_id=item.id,
                actor_id=user_id,
                from_owner_id=item.owner_id,
                to_owner_id=loan_request.requester_id,
                event_type="transfer",
                notes=f"Loan approved for request #{loan_request.id}",
            )
            db.session.add(custody_event)
        else:
            loan_request.status = "rejected"

        # Check if loan_request has federated metadata in notes to dispatch Accept/Reject activity
        if loan_request.notes and "[Federated Offer from" in loan_request.notes:
            try:
                import json
                import uuid

                lines = loan_request.notes.split("\n", 1)
                if len(lines) > 1:
                    fed_meta = json.loads(lines[1])
                    inbox_url = fed_meta.get("inbox_url")
                    orig_activity_id = fed_meta.get("remote_activity_id")
                    target_actor_uri = fed_meta.get("remote_actor_uri")
                    if inbox_url:
                        from app.core.federation_client import FederationClient
                        from app.core.iri import canonical_actor_iri, get_federation_base_url

                        base_url = get_federation_base_url()
                        local_actor_uri = canonical_actor_iri(user_id, base_url)
                        activity_type = "Accept" if action == "approve" else "Reject"
                        resp_activity = {
                            "@context": "https://www.w3.org/ns/activitystreams",
                            "id": f"{base_url}/activities/{activity_type.lower()}-{uuid.uuid4()}",
                            "type": activity_type,
                            "actor": local_actor_uri,
                            "object": {
                                "id": orig_activity_id,
                                "type": "Offer",
                                "actor": target_actor_uri,
                                "object": f"{base_url}/items/{item.id}",
                            },
                        }
                        client = FederationClient()
                        client.post_to_inbox(inbox_url, resp_activity, sender_user_id=str(user_id))
            except Exception as exc:
                logger.warning("Could not dispatch federated %s response: %s", action, exc)

        db.session.commit()

        try:
            from app.core.notifications import create_notification

            if loan_request.requester_id:
                notif_type = "loan_approved" if action == "approve" else "loan_rejected"
                create_notification(
                    user_id=loan_request.requester_id,
                    notification_type=notif_type,
                    payload={
                        "item_id": item.id,
                        "loan_request_id": loan_request.id,
                        "action": action,
                        "message": f"Your loan request for item #{item.id} was {loan_request.status}",
                    },
                    target_iri=f"/items/{item.id}",
                )
        except Exception as notif_err:
            logger.warning("Failed to emit loan resolution notification: %s", notif_err)

        return jsonify({"success": True, "data": loan_request.to_dict()}), 200
    except SQLAlchemyError as e:
        logger.error("Error resolving loan request %s: %s", request_id, e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@lending_bp.route("/items/<int:item_id>/loan-status", methods=["GET"])
@limiter.limit("60 per minute")
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


@lending_bp.route("/items/<int:item_id>/return", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def return_loaned_item(item_id: int) -> Response | tuple[Response, int]:
    """Owner or borrower marks a lent item as returned to custody."""
    from app.db.auth import User
    from app.db.core import Item, ItemCustodyEvent, ItemStatusLog, db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"error": "Item not found", "code": 404}), 404

    user = db.session.get(User, user_id)
    is_admin = user and any(role.name == "admin" for role in getattr(user, "roles", []))
    is_owner = str(item.owner_id) == str(user_id)
    is_borrower = str(item.lent_to_user_id) == str(user_id)

    if not (is_owner or is_borrower or is_admin):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    if item.collection_status != "lent":
        return jsonify({"error": "Item is not currently marked as lent", "code": 400}), 400

    old_borrower_id = item.lent_to_user_id
    item.collection_status = "available"
    item.lent_to_user_id = None

    status_log = ItemStatusLog(
        item_id=item.id,
        user_id=user_id,
        old_status="lent",
        new_status="available",
    )
    db.session.add(status_log)

    custody_event = ItemCustodyEvent(
        item_id=item.id,
        actor_id=user_id,
        from_owner_id=old_borrower_id,
        to_owner_id=item.owner_id,
        event_type="return",
        notes=f"Item returned from loan by user {user_id}",
    )
    db.session.add(custody_event)
    db.session.commit()

    return jsonify({"success": True, "data": item.to_dict()}), 200


@lending_bp.route("/federated-request", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def request_federated_loan() -> Response | tuple[Response, int]:
    """Send an outbound ActivityPub Offer (loan request) to a remote friend."""
    import uuid

    from app.core.federation_client import FederationClient
    from app.core.iri import canonical_actor_iri, get_federation_base_url
    from app.db.auth import User
    from app.db.core import db

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401
    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    data = request.get_json() or {}
    target_item_uri = data.get("target_item_uri")
    target_actor_uri = data.get("target_actor_uri")
    notes = data.get("notes") or "Requesting loan of item"

    if not target_item_uri or not target_actor_uri:
        return jsonify({"error": "target_item_uri and target_actor_uri are required", "code": 400}), 400

    client = FederationClient()
    actor_doc = client.fetch_actor(target_actor_uri)
    if not actor_doc or not isinstance(actor_doc, dict):
        return jsonify({"error": f"Failed to resolve remote actor {target_actor_uri}", "code": 502}), 502

    inbox_url = actor_doc.get("inbox")
    if not inbox_url:
        return jsonify({"error": "Remote actor lacks inbox endpoint", "code": 400}), 400

    base_url = get_federation_base_url()
    local_actor_uri = canonical_actor_iri(current_user.id, base_url)
    activity_id = f"{base_url}/activities/offer-{uuid.uuid4()}"

    offer_activity: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": activity_id,
        "type": "Offer",
        "actor": local_actor_uri,
        "object": target_item_uri,
        "target": target_actor_uri,
        "notes": notes,
    }

    try:
        resp = client.post_to_inbox(inbox_url, offer_activity, sender_user_id=str(current_user.id))
        if resp.status_code in (200, 201, 202):
            return (
                jsonify(
                    {
                        "success": True,
                        "status": "delivered",
                        "activity": offer_activity,
                    }
                ),
                201,
            )
        return (
            jsonify(
                {
                    "error": f"Remote inbox returned HTTP {resp.status_code}",
                    "code": resp.status_code,
                }
            ),
            resp.status_code,
        )
    except Exception as exc:
        logger.error("Failed to dispatch outbound Offer to %s: %s", inbox_url, exc)
        return jsonify({"error": "Failed to deliver loan Offer", "code": 500}), 500


@lending_bp.route("/test/reset", methods=["POST"])
@limiter.limit("30 per minute")
def reset_lending_test_state() -> Response | tuple[Response, int]:
    """E2E test helper: resets all lender items to available and deletes loan requests.

    The `TESTING` flag alone is not a sufficient gate. It is set only through
    `create_app(config_override=...)`, which no deployment path currently uses --
    but the route carries no authentication of its own, so any future change that
    made `TESTING` settable from the environment would turn this into an
    unauthenticated, state-mutating endpoint that resets every lent Item and
    deletes every loan request. The shared-secret check below bounds that blast
    radius: a mistake in how `TESTING` is configured would no longer be
    sufficient on its own to expose the endpoint.
    """
    from flask import current_app, request

    is_prod = os.environ.get("FLASK_ENV") == "production" or current_app.config.get("ENV") == "production"
    if is_prod or not current_app.config.get("TESTING"):
        return jsonify({"error": "Forbidden", "code": 403}), 403

    # Constant-time comparison: a `!=` on a shared secret is a timing oracle,
    # and this endpoint is reachable by anyone who can reach the API.
    expected = current_app.config.get("E2E_RESET_SECRET") or os.environ.get("E2E_RESET_SECRET", "")
    if not expected:
        # Fail closed. Without a configured secret there is no way to
        # distinguish the E2E harness from any other caller, so the endpoint
        # stays closed rather than becoming open to anyone who sets TESTING.
        logger.error(
            "Refusing /lending/test/reset: E2E_RESET_SECRET is not configured. "
            "Set it to a shared secret for the E2E harness; see .env.example."
        )
        return jsonify({"error": "Forbidden", "code": 403}), 403

    provided = request.headers.get("X-E2E-Reset-Secret", "")
    if not hmac.compare_digest(provided, expected):
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
