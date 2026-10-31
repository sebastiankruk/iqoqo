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
from flask import Blueprint, Response, current_app, g, jsonify, request
from sqlalchemy import select

from app.api.core import api_bp, invalid_json_payload_response
from app.core.account_lifecycle import pending_deletion_state
from app.core.limiter import limiter
from app.db.models import ConsentRecord, FederationConsent, User, db
from app.utils.http_client import is_safe_url

from .decorators import require_auth

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

#: Maximum accepted biography length, in characters.
BIO_MAX_LENGTH = 500


def _apply_bio(user: User, raw_bio) -> Response | None:
    """Sanitize and length-check a biography, then assign it to ``user``.

    Shared by every profile write path (``PUT /api/profile/`` and
    ``PATCH /api/profile/settings``) so the two cannot drift apart: an
    unsanitized or oversized bio must be rejected no matter which endpoint
    the client reaches for.

    Returns a ready-to-return ``Response`` on rejection, or ``None`` when the
    value was accepted and assigned. ``None`` clears the biography.
    """
    if raw_bio is None:
        user.bio = None
        return None

    clean_bio = bleach.clean(str(raw_bio).strip(), tags=[], attributes={}, protocols=[], strip=True)
    if len(clean_bio) > BIO_MAX_LENGTH:
        return jsonify({"error": f"Biography cannot exceed {BIO_MAX_LENGTH} characters", "code": 400}), 400

    user.bio = clean_bio
    return None


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

    # `to_private_dict`, not `to_dict`: the verification state belongs to the
    # owner, and this is the only surface that reports it.
    data = user.to_private_dict()
    data.update(
        {
            "roles": [r.name for r in user.roles],
            "permissions": permissions,
            "consents": consents,
        }
    )
    data["deletion"] = pending_deletion_state(user)

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
    is_granted = bool(data.get("is_granted", data.get("granted", False)))

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

    if consent_type == "federation":
        fed_consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
        if not fed_consent:
            fed_consent = FederationConsent(
                user_id=user.id,
                federated_profile=is_granted,
                federated_collection=is_granted,
            )
            db.session.add(fed_consent)
        else:
            fed_consent.federated_profile = is_granted
            if not is_granted:
                fed_consent.federated_collection = False
            fed_consent.updated_at = datetime.now(UTC)

        if is_granted and not user.federation_public_key:
            from app.core import federation_keys
            from app.core.iri import canonical_actor_iri, get_federation_base_url

            try:
                base_url = get_federation_base_url()
                existing_pub = federation_keys.get_actor_public_key(str(user.id))
                if existing_pub:
                    public_key_pem = existing_pub
                else:
                    _, public_key_pem = federation_keys.generate_actor_keypair(str(user.id))
                canonical_uri = canonical_actor_iri(user.id, base_url)
                user.federation_public_key = public_key_pem
                user.federation_key_id = f"{canonical_uri}#main-key"
            except Exception as exc:
                current_app.logger.warning("Failed generating keypair during consent grant: %s", exc)

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
        err = _apply_bio(user, data["bio"])
        if err:
            return err

    valid_visibilities = ["public", "friends_only", "shared", "private"]
    if "visibility" in data:
        val = data["visibility"]
        if val in valid_visibilities:
            user.visibility = "friends_only" if val == "shared" else val
        else:
            return jsonify({"error": f"Invalid visibility. Must be one of {valid_visibilities}", "code": 400}), 400

    if "default_item_visibility" in data:
        val = data["default_item_visibility"]
        if val in valid_visibilities:
            user.default_item_visibility = "friends_only" if val == "shared" else val
        else:
            return (
                jsonify({"error": f"Invalid default_item_visibility. Must be one of {valid_visibilities}", "code": 400}),
                400,
            )

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
    """Right to be forgotten.

    Account deletion is no longer a single authenticated call, and this
    endpoint is where that used to live.  It now refuses and points at the
    confirmed flow rather than deleting anything, because a request that
    irreversibly removes an account on the strength of a session cookie alone
    is exactly what the confirmation flow exists to prevent.

    It is not removed, and not aliased to a bypass: a caller that treats a 409
    as "not implemented yet" and retries is harmless, whereas a silent
    auto-forward to an unconditional delete would undo the whole design.  The
    client must call ``POST /api/account/deletion/request``, follow the emailed
    link, and submit the confirmation.
    """
    return (
        jsonify(
            {
                "error": "Account deletion requires confirmation by email. "
                "Start a request with POST /api/account/deletion/request and follow the link you receive.",
                "code": 409,
                "replacement": "/api/account/deletion/request",
            }
        ),
        409,
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
        err = _apply_bio(user, data["bio"])
        if err:
            return err

    if "visibility" in data:
        # User feedback: reuse visibility to value == public
        val = data["visibility"]
        if val in ["public", "friends_only", "shared", "private"]:
            user.visibility = val
        else:
            return jsonify({"error": "Invalid visibility. Must be 'public', 'friends_only', or 'private'", "code": 400}), 400

    if "default_item_visibility" in data:
        val = data["default_item_visibility"]
        if val in ["public", "friends_only", "shared", "private"]:
            user.default_item_visibility = val
        else:
            return jsonify({"error": "Invalid default_item_visibility. Must be 'public', 'friends_only', or 'private'", "code": 400}), 400

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated successfully.", "data": user.to_dict()})


@profile_bp.route("/friends", methods=["GET"])
@require_auth
def get_user_friends():
    """List current user's accepted friends and pending requests."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    from app.core.friend_service import list_friends

    data = list_friends(user_id)
    return jsonify({"success": True, "data": data})


@profile_bp.route("/friends/request", methods=["POST"])
@require_auth
def send_user_friend_request():
    """Send a friend request by username, email, or federated handle."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    identifier = payload.get("identifier") or payload.get("username") or payload.get("email")
    if not identifier:
        return jsonify({"error": "Target user identifier is required", "code": 400}), 400

    from app.core.friend_service import send_friend_request

    data, err, status_code = send_friend_request(user_id, identifier)
    if err:
        return jsonify({"error": err, "code": status_code}), status_code

    return jsonify({"success": True, "data": data, "message": "Friend request sent successfully."}), status_code


@profile_bp.route("/friends/<friendship_id>/respond", methods=["POST"])
@require_auth
def respond_user_friend_request(friendship_id: str):
    """Accept or reject an incoming friend request."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if not action or action not in ("accept", "reject"):
        return jsonify({"error": "Invalid action. Must be 'accept' or 'reject'", "code": 400}), 400

    from app.core.friend_service import respond_friend_request

    data, err, status_code = respond_friend_request(user_id, friendship_id, action)
    if err:
        return jsonify({"error": err, "code": status_code}), status_code

    return jsonify({"success": True, "data": data}), status_code


@profile_bp.route("/friends/<friendship_id>", methods=["DELETE"])
@require_auth
def delete_user_friend(friendship_id: str):
    """Remove a friend or cancel a pending request."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.friend_service import remove_friend

    ok, err, status_code = remove_friend(user_id, friendship_id)
    if err:
        return jsonify({"error": err, "code": status_code}), status_code

    return jsonify({"success": True, "message": "Friendship removed."}), status_code


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


def _handle_get_federation_consent() -> tuple[Response, int] | Response:
    """Core logic to retrieve current user's federation consent."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "data": None, "error": "User not found"}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    if not consent:
        data = {
            "user_id": str(user.id),
            "federated_profile": False,
            "federated_collection": False,
            "auto_accept_follows": False,
            "updated_at": None,
        }
    else:
        data = consent.to_dict()

    return jsonify({"success": True, "data": data, "error": None}), 200


def _handle_update_federation_consent() -> tuple[Response, int] | Response:
    """Core logic to update current user's federation consent."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "data": None, "error": "User not found"}), 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return invalid_json_payload_response()

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    if not consent:
        consent = FederationConsent(
            user_id=user.id,
            federated_profile=bool(payload.get("federated_profile", False)),
            federated_collection=bool(payload.get("federated_collection", False)),
            auto_accept_follows=bool(payload.get("auto_accept_follows", False)),
        )
        db.session.add(consent)
    else:
        if "federated_profile" in payload:
            consent.federated_profile = bool(payload["federated_profile"])
        if "federated_collection" in payload:
            consent.federated_collection = bool(payload["federated_collection"])
        if "auto_accept_follows" in payload:
            consent.auto_accept_follows = bool(payload["auto_accept_follows"])
        consent.updated_at = datetime.now(UTC)

    # Trigger actor RSA keypair generation on initial opt-in
    if consent.federated_profile or consent.federated_collection:
        from app.core import federation_keys
        from app.core.iri import canonical_actor_iri, get_federation_base_url

        has_key = bool(user.federation_public_key)
        if not has_key:
            try:
                has_key = bool(federation_keys.get_actor_public_key(str(user.id)))
            except Exception:
                has_key = False

        if not has_key:
            try:
                base_url = get_federation_base_url()
                key_id_suffix, public_key_pem = federation_keys.generate_actor_keypair(str(user.id))
                canonical_uri = canonical_actor_iri(user.id, base_url)
                user.federation_public_key = public_key_pem
                user.federation_key_id = f"{canonical_uri}#main-key"
            except Exception as e:
                current_app.logger.warning("Failed to generate actor keypair on opt-in: %s", e)

    db.session.commit()
    return jsonify({"success": True, "data": consent.to_dict(), "message": "Federation consent updated", "error": None}), 200


@profile_bp.route("/federation-consent", methods=["GET"])
@require_auth
def get_federation_consent():
    """Retrieve federation consent settings for current user."""
    return _handle_get_federation_consent()


@profile_bp.route("/federation-consent", methods=["PUT", "PATCH"])
@require_auth
def update_federation_consent():
    """Update federation consent settings for current user."""
    return _handle_update_federation_consent()


@api_bp.route("/v1/profile/federation-consent", methods=["GET"])
@require_auth
def get_federation_consent_v1():
    """Retrieve federation consent settings via v1 profile endpoint."""
    return _handle_get_federation_consent()


@api_bp.route("/v1/profile/federation-consent", methods=["PUT", "PATCH"])
@require_auth
def update_federation_consent_v1():
    """Update federation consent settings via v1 profile endpoint."""
    return _handle_update_federation_consent()
