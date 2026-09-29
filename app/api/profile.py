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
"""Public user profile and collection endpoints.

Profiles are authenticated but not privileged: the routes expose only what a
profile owner or a permitted viewer may see, and hide entries through visibility
flags rather than by omitting them from the query."""

from datetime import UTC, datetime
from urllib.parse import urlparse

import bleach
from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import select

from app.core.limiter import limiter
from app.db.models import ConsentRecord, User, db
from app.utils.http_client import is_safe_url

from .decorators import require_auth

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("/", methods=["GET"], strict_slashes=False)
@require_auth
def get_profile():
    """Return the caller's own profile, roles and resolved permissions.

    Permissions are unioned across every role the user holds, so the response
    reflects what the user can actually do rather than what any single role grants."""
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    consents = {c.consent_type: c.is_granted for c in user.consents}

    # Extract unique permissions from all roles the user holds and return them
    permissions = sorted({perm.name for role in user.roles for perm in role.permissions})

    data = user.to_dict()
    data.update(
        {
            "roles": [r.name for r in user.roles],
            "permissions": permissions,
            "consents": consents,
        }
    )

    return jsonify(
        {
            "success": True,
            "data": data,
        }
    )


@profile_bp.route("/consent", methods=["POST"])
@require_auth
def update_consent():
    """Grant or revoke a single consent type.

    Consent is recorded as a row with an explicit boolean rather than by deleting
    it, so a withdrawal is auditable after the fact."""
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
    """Update the caller's display name and profile fields.

    Restricted to self-service fields. Role and permission changes are not reachable
    here; they belong to the admin blueprint."""
    data = request.get_json()
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "display_name" in data:
        raw_name = data["display_name"]
        if raw_name is not None:
            user.display_name = bleach.clean(str(raw_name).strip(), tags=[], attributes={}, protocols=[], strip=True)
        else:
            user.display_name = None

    if "public_username" in data:
        err = _set_public_username(user, data["public_username"])
        if err:
            return err

    if "bio" in data:
        bio_val = data["bio"]
        if bio_val is not None:
            clean_bio = bleach.clean(str(bio_val).strip(), tags=[], attributes={}, protocols=[], strip=True)
            if len(clean_bio) > 500:
                return jsonify({"error": "Biography cannot exceed 500 characters", "code": 400}), 400
            user.bio = clean_bio
        else:
            user.bio = None

    if "visibility" in data:
        val = data["visibility"]
        if val in ["public", "private"]:
            user.visibility = val

    if "avatar_url" in data:
        raw_avatar = data["avatar_url"]
        if raw_avatar:
            avatar_url = str(raw_avatar).strip()
            if urlparse(avatar_url).scheme != "https" or not is_safe_url(avatar_url):
                return jsonify({"error": "Invalid or unsafe avatar URL", "code": 400}), 400
            user.avatar_url = avatar_url
        else:
            user.avatar_url = None

    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "data": user.to_dict()})


@profile_bp.route("/", methods=["DELETE"], strict_slashes=False)
@require_auth
def delete_profile():
    """Right to be forgotten: Temporarily disabled pending email confirmation flow (C33, v0.8.2)."""
    return (
        jsonify(
            {
                "error": "Account deletion temporarily disabled — email confirmation required (v0.8.2)",
                "code": 501,
            }
        ),
        501,
    )


def _set_public_username(user: User, new_username: str | None) -> Response | tuple[Response, int] | None:
    """Helper to validate and update public username, preventing duplicates."""
    if new_username is not None:
        clean_username = new_username.strip().lower()
        if clean_username:
            stmt = select(User).where(User.public_username == clean_username, User.id != user.id)
            existing = db.session.execute(stmt).scalar_one_or_none()
            if existing:
                return jsonify({"error": "Public username is already taken."}), 409
            user.public_username = clean_username
        else:
            user.public_username = None
    return None


def _mask_email(email: str) -> str:
    """Masks an email to prevent PII scraping (e.g., a***z@example.com)."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) > 2:
        local = f"{local[0]}***{local[-1]}"
    else:
        local = f"{local[0]}***"
    return f"{local}@{domain}"


@profile_bp.route("/users/search", methods=["GET"], strict_slashes=False)
@profile_bp.route("/search", methods=["GET"], strict_slashes=False)
@require_auth
@limiter.limit("30 per minute")
def search_users():
    """Search for other users by exact email or partial display name."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"success": True, "data": []})

    limit_param = request.args.get("limit", 10, type=int)
    if limit_param is None or limit_param < 1:
        return jsonify({"success": False, "data": None, "error": "Invalid limit parameter"}), 400
    limit = min(limit_param, 20)

    current_user_id = getattr(g, "user_id", None)

    users = (
        User.query.filter(
            db.and_(
                User.is_active.is_(True),
                User.id != current_user_id,
                db.or_(User.email == query.lower(), User.display_name.ilike(f"%{query}%")),
            )
        )
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": str(u.id),
            "email": u.email if u.email == query.lower() else _mask_email(u.email),
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
        }
        for u in users
    ]
    return jsonify({"success": True, "data": results})


@profile_bp.route("/settings", methods=["PATCH"])
@require_auth
def update_profile_settings():
    """Updates the current user's public profile settings."""
    data = request.get_json() or {}
    user = db.session.get(User, getattr(g, "user_id", None))
    if not user:
        return jsonify({"error": "User not found"}), 404

    if "public_username" in data:
        new_username = data["public_username"]
        if new_username and new_username.strip():
            err = _set_public_username(user, new_username)
            if err:
                return err

    if "bio" in data:
        user.bio = data["bio"].strip()

    if "visibility" in data:
        # User feedback: reuse visibility to value == public
        val = data["visibility"]
        if val in ["public", "private"]:
            user.visibility = val

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully.", "data": user.to_dict()})


@profile_bp.route("/insights/velocity", methods=["GET"], strict_slashes=False)
@require_auth
def get_insights_velocity():
    """Returns acquisition velocity data for the authenticated user or globally."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    from app.core.data_manager import get_velocity_stats

    scope = request.args.get("scope", "personal")
    owner_id = user_id if scope != "global" else None
    data = get_velocity_stats(owner_id)
    return jsonify({"success": True, "data": data})


@profile_bp.route("/insights/distribution", methods=["GET"], strict_slashes=False)
@require_auth
def get_insights_distribution():
    """Returns media type and format distribution data for the authenticated user or globally."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    from app.core.data_manager import get_distribution_stats

    scope = request.args.get("scope", "personal")
    owner_id = user_id if scope != "global" else None
    data = get_distribution_stats(owner_id)
    return jsonify({"success": True, "data": data})
