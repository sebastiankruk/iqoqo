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
import hmac
import logging
import time
import uuid
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.core.cache import cache
from app.core.permissions import PermissionName
from app.db.models import TokenBlocklist, User, db

logger = logging.getLogger(__name__)

_REVOCATION_CACHE_PREFIX = "token:revoked:"
_CACHE_REVOKED = "revoked"
_CACHE_ACTIVE = "active"
_DEFAULT_TOKEN_CACHE_TTL = 60
_MAX_TOKEN_CACHE_TTL = 7 * 24 * 60 * 60


def _revocation_cache_timeout(expires_at: int | float | None) -> int:
    """Return a bounded cache TTL that never extends beyond the JWT lifetime."""
    if expires_at is None:
        return _DEFAULT_TOKEN_CACHE_TTL
    return max(1, min(int(expires_at - time.time()), _MAX_TOKEN_CACHE_TTL))


def _cache_value(value: object) -> str | None:
    if isinstance(value, bytes):
        try:
            value = value.decode("ascii")
        except UnicodeDecodeError:
            return None
    return value if isinstance(value, str) else None


def cache_token_revoked(jti: str | None, expires_at: int | float | None) -> None:
    """Publish a persisted revocation to the cache without weakening DB fallback."""
    if not jti:
        return
    try:
        cache.set(f"{_REVOCATION_CACHE_PREFIX}{jti}", _CACHE_REVOKED, timeout=_revocation_cache_timeout(expires_at))
    except Exception:
        logger.warning("Could not cache token revocation; PostgreSQL remains authoritative", exc_info=True)


def _is_token_revoked(jti: str | None, expires_at: int | float | None = None) -> bool:
    """Use Redis/Flask cache first and PostgreSQL on cache misses or failures."""
    if not jti:
        return False

    cache_key = f"{_REVOCATION_CACHE_PREFIX}{jti}"
    cache_timeout = _revocation_cache_timeout(expires_at)
    try:
        cached = _cache_value(cache.get(cache_key))
        if cached == _CACHE_REVOKED:
            return True
        if cached == _CACHE_ACTIVE:
            return False
    except Exception:
        # Redis is an optimization only; PostgreSQL remains the source of truth.
        logger.warning("Token revocation cache lookup failed; falling back to PostgreSQL", exc_info=True)

    entry = db.session.execute(db.select(TokenBlocklist).filter_by(jti=jti)).scalars().first()
    revoked = bool(entry and entry.jti and hmac.compare_digest(entry.jti, jti))

    try:
        if revoked:
            cache.set(cache_key, _CACHE_REVOKED, timeout=cache_timeout)
        elif not cache.add(cache_key, _CACHE_ACTIVE, timeout=cache_timeout):
            # Do not overwrite a concurrent logout's positive cache entry with
            # a stale negative lookup result.
            if _cache_value(cache.get(cache_key)) == _CACHE_REVOKED:
                revoked = True
    except Exception:
        logger.warning("Could not update token revocation cache; PostgreSQL remains authoritative", exc_info=True)

    return revoked


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        # 2. Fallback to Cookie
        elif "iqoqo_session" in request.cookies:
            token = request.cookies.get("iqoqo_session")

        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

            # Check blocklist
            if _is_token_revoked(payload.get("jti"), payload.get("exp")):
                return jsonify({"error": "Token revoked"}), 401

            g.user_id = uuid.UUID(payload["sub"])

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except ValueError:
            # Catches cases where the 'sub' is not a properly formatted UUID string
            return jsonify({"error": "Invalid user ID format"}), 401

        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            parts = auth_header.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        elif "iqoqo_session" in request.cookies:
            token = request.cookies.get("iqoqo_session")

        g.user_id = None
        if token:
            try:
                payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
                if not _is_token_revoked(payload.get("jti"), payload.get("exp")):
                    g.user_id = uuid.UUID(payload["sub"])
            except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, jwt.DecodeError, KeyError):
                pass

        return f(*args, **kwargs)

    return decorated


def require_permission(perm_name: PermissionName):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Enforce strict usage of PermissionName
            if not isinstance(perm_name, PermissionName):
                raise TypeError(f"require_permission expects PermissionName Enum, got {type(perm_name)}")

            user_id = getattr(g, "user_id", None)
            if not user_id:
                return jsonify({"error": "Authentication required"}), 401

            user = db.session.get(User, user_id)
            if not user or not user.has_permission(perm_name):
                return jsonify({"error": "Forbidden", "missing_permission": perm_name.value}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        user = db.session.get(User, user_id)
        is_admin = any(role.name == "admin" for role in getattr(user, "roles", [])) if user else False
        if not is_admin:
            return jsonify({"success": False, "error": "Admin privileges required"}), 403

        return f(*args, **kwargs)

    return decorated_function


def require_physical_item(f):
    """Declarative FRBR boundary interceptor for item-level route handlers.

    Rejects any request whose ``item_id`` route parameter is ``<= 0``.
    Virtual wishlist items carry negative IDs (``-intent_id``) and ``0`` is
    not a valid entity at any FRBR level.  Applying this decorator to a
    route makes the FRBR boundary check explicit and eliminates the brittle
    inline ``if item_id <= 0:`` guards that would otherwise be scattered
    across every handler.

    Usage::

        @api_bp.route("/items/<int(signed=True):item_id>/some-action", methods=["POST"])
        @require_auth
        @require_physical_item
        def some_physical_action(item_id: int):
            ...  # item_id is guaranteed to be > 0 here

    Raises a ``400 Bad Request`` with a structured JSON payload when the
    interceptor rejects the request, consistent with the project-wide error
    format ``{"error": "...", "code": 400}``.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        item_id = kwargs.get("item_id")
        if item_id is not None and item_id <= 0:
            return (
                jsonify(
                    {
                        "error": ("Cannot mutate virtual items (id <= 0). " "Physical item IDs must be strictly positive."),
                        "code": 400,
                    }
                ),
                400,
            )
        return f(*args, **kwargs)

    return decorated
