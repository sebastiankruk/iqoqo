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
from flask import current_app, jsonify, request

from app.db.models import User, db


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

            # FIX: Convert the string back to a UUID object
            request.user_id = uuid.UUID(payload["sub"])

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except ValueError:
            # Catches cases where the 'sub' is not a properly formatted UUID string
            return jsonify({"error": "Invalid user ID format"}), 401

        return f(*args, **kwargs)

    return decorated


def require_permission(perm_name):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = db.session.get(User, request.user_id)
            if not user or not user.has_permission(perm_name):
                return jsonify({"error": "Forbidden", "missing_permission": perm_name}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator
