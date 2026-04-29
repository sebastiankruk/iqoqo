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
from datetime import UTC, datetime

from flask import Blueprint, g, jsonify, request

from app.db.models import ConsentRecord, User, db

from .decorators import require_auth

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("/", methods=["GET"], strict_slashes=False)
@require_auth
def get_profile():
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    consents = {c.consent_type: c.is_granted for c in user.consents}

    # Extract unique permissions from all roles the user holds and return them
    permissions = sorted({perm.name for role in user.roles for perm in role.permissions})

    return jsonify(
        {
            "success": True,
            "data": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "visibility": user.visibility,
                "roles": [r.name for r in user.roles],
                "permissions": permissions,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "consents": consents,
            },
        }
    )


@profile_bp.route("/consent", methods=["POST"])
@require_auth
def update_consent():
    data = request.get_json()
    consent_type = data.get("consent_type")
    is_granted = data.get("is_granted", False)

    if not consent_type:
        return jsonify({"error": "Missing consent_type"}), 400

    user = db.session.get(User, getattr(g, "user_id", None))
    existing_consent = ConsentRecord.query.filter_by(user_id=user.id, consent_type=consent_type).first()

    if existing_consent:
        existing_consent.is_granted = is_granted
        existing_consent.timestamp = datetime.now(UTC)
    else:
        new_consent = ConsentRecord(user_id=user.id, consent_type=consent_type, is_granted=is_granted, policy_version="v0.1.0")
        db.session.add(new_consent)

    db.session.commit()
    return jsonify({"message": "Consent updated successfully"})


# Add PUT and DELETE to profile_bp in app/api/profile.py


@profile_bp.route("/", methods=["PUT"], strict_slashes=False)
@require_auth
def update_profile():
    data = request.get_json()
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "display_name" in data:
        user.display_name = data["display_name"]

    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "display_name": user.display_name})


@profile_bp.route("/", methods=["DELETE"], strict_slashes=False)
@require_auth
def delete_profile():
    """Right to be forgotten: Deletes user, their items, and consents."""
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Because of foreign key constraints with ondelete="CASCADE" in DB models,
    # deleting the user will automatically remove their Item and ConsentRecord entries.
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "Account and all associated data permanently deleted."}), 200


@profile_bp.route("/users/search", methods=["GET"], strict_slashes=False)
@require_auth
def search_users():
    """Search for other users by email or display name. Used for lending items."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"success": True, "data": []})

    limit = min(request.args.get("limit", 10, type=int), 20)

    # Note: the user must be active. We allow finding any active user so items can be lent.
    # Exclude the current user from search results.
    current_user_id = getattr(g, "user_id", None)

    users = (
        User.query.filter(
            db.and_(
                User.is_active.is_(True),
                User.id != current_user_id,
                db.or_(User.email.ilike(f"%{query}%"), User.display_name.ilike(f"%{query}%")),
            )
        )
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
        }
        for u in users
    ]

    return jsonify({"success": True, "data": results})
