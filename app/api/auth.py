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

import os
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, jsonify, redirect, request

from app.db.models import Role, User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    if app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def generate_internal_jwt(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "roles": [role.name for role in user.roles],  # type: ignore[attr-defined]
        "exp": datetime.now(UTC) + timedelta(hours=12),
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


@auth_bp.route("/login/google")
def google_login():
    redirect_uri = request.url_root + "api/auth/callback/google"
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback/google")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token, nonce=None)
    email = user_info.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, display_name=user_info.get("name"), is_active=True, google_id=user_info.get("sub"))
        default_role = Role.query.filter_by(name="user").first()
        if default_role:
            user.roles.append(default_role)
        db.session.add(user)

    user.last_login = datetime.now(UTC)
    db.session.commit()

    internal_token = generate_internal_jwt(user)
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")

    # Updated redirect path
    return redirect(f"{frontend_url}/api/auth-exchange?token={internal_token}")


@auth_bp.route("/login", methods=["POST"])
def local_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error": "Suspended"}), 403

    user.last_login = datetime.now(UTC)
    db.session.commit()
    return jsonify({"token": generate_internal_jwt(user), "user": {"id": str(user.id), "email": user.email}})


@auth_bp.route("/register", methods=["POST"])
def local_register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    display_name = data.get("display_name")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create new user
    new_user = User(email=email, display_name=display_name, is_active=True)
    new_user.set_password(password)

    # Assign default 'user' role
    default_role = Role.query.filter_by(name="user").first()
    if default_role:
        new_user.roles.append(default_role)

    db.session.add(new_user)
    db.session.commit()

    # Automatically log the user in by generating a token
    internal_token = generate_internal_jwt(new_user)

    return (
        jsonify(
            {"message": "User registered successfully", "token": internal_token, "user": {"id": str(new_user.id), "email": new_user.email}}
        ),
        201,
    )
