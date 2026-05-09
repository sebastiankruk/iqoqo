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
import uuid
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.core.permissions import PermissionName
from app.db.models import TokenBlocklist, User, db


def _is_token_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    return db.session.query(TokenBlocklist.id).filter_by(jti=jti).first() is not None


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
            if _is_token_revoked(payload.get("jti")):
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
                if not _is_token_revoked(payload.get("jti")):
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

            perm = perm_name.value
            user = db.session.get(User, getattr(g, "user_id", None))
            if not user or not user.has_permission(perm):
                return jsonify({"error": "Forbidden", "missing_permission": perm}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def _get_user_id_from_token(token: str) -> tuple[uuid.UUID | None, str | None]:
    """Helper to validate token and return user_id or error message."""
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        if _is_token_revoked(payload.get("jti")):
            return None, "Token revoked"
        return uuid.UUID(payload["sub"]), None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"
    except ValueError:
        return None, "Invalid user ID format"


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = (
            request.headers.get("Authorization", "").split(" ")[1]
            if "Authorization" in request.headers
            else request.cookies.get("iqoqo_session")
        )

        if not token:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        uid, err = _get_user_id_from_token(token)
        if err:
            return jsonify({"success": False, "error": err}), 401

        g.user_id = uid
        user = db.session.get(User, uid)
        is_admin = any(role.name == "admin" for role in getattr(user, "roles", [])) if user else False
        if not is_admin:
            return jsonify({"success": False, "error": "Admin privileges required"}), 403

        return f(*args, **kwargs)

    return decorated_function
