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

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import jwt as pyjwt
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, jsonify, redirect, request, session
from joserfc.errors import JoseError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.models import Role, TokenBlocklist, User, db

logger = logging.getLogger(__name__)

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
        "jti": str(uuid.uuid4()),  # Unique ID for revocation
        "email": user.email,
        "roles": [role.name for role in user.roles],  # type: ignore[attr-defined]
        "exp": datetime.now(UTC) + timedelta(days=7),  # matches the session cookie lifetime
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


@auth_bp.route("/login/google")
def google_login():
    callback_url = request.args.get("callbackUrl") or request.args.get("redirect")
    if callback_url and callback_url.startswith("/") and not callback_url.startswith("//"):
        session["oauth_callback_url"] = callback_url

    redirect_uri = request.url_root + "api/auth/callback/google"
    original_uri = redirect_uri

    # Bulletproof Fail-safe: Force HTTPS in production/preview environments
    # just in case Nginx proxy headers strip the secure scheme.
    if redirect_uri.startswith("http://") and os.getenv("FLASK_ENV") == "production":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    logger.info("Google OAuth redirect_uri: %s (original: %s)", redirect_uri, original_uri)

    try:
        return oauth.google.authorize_redirect(redirect_uri)
    except OAuthError as e:
        logger.error("Google OAuth authorize_redirect failed: %s", e, exc_info=True)
        return jsonify({"error": f"OAuth init failed: {e}"}), 502


@auth_bp.route("/callback/google")
def google_callback():
    callback_url = session.pop("oauth_callback_url", None)

    try:
        token = oauth.google.authorize_access_token()
    except OAuthError as e:
        logger.error("Google OAuth token exchange failed: %s", e, exc_info=True)
        return redirect(f"{os.getenv('NEXT_PUBLIC_FRONTEND_URL', 'http://localhost:3000')}/login?error=token_exchange_failed")

    try:
        user_info = oauth.google.parse_id_token(token, nonce=None)
    except JoseError as e:
        logger.error("Google OAuth parse_id_token failed: %s", e, exc_info=True)
        return redirect(f"{os.getenv('NEXT_PUBLIC_FRONTEND_URL', 'http://localhost:3000')}/login?error=id_token_parse_failed")

    email = user_info.get("email")
    if not email:
        logger.error("Google OAuth: no email in user_info: %s", user_info)
        return redirect(f"{os.getenv('NEXT_PUBLIC_FRONTEND_URL', 'http://localhost:3000')}/login?error=no_email")

    picture = user_info.get("picture")
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")

    try:
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                display_name=user_info.get("name"),
                is_active=True,
                google_id=user_info.get("sub"),
                avatar_url=picture,
            )
            default_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
            if default_role:
                user.roles.append(default_role)
            db.session.add(user)
        else:
            if picture and user.avatar_url != picture:
                user.avatar_url = picture

        user.last_login = datetime.now(UTC)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Google OAuth user creation/update failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=user_setup_failed")

    try:
        internal_token = generate_internal_jwt(user)
    except pyjwt.PyJWTError as e:
        logger.error("Google OAuth JWT generation failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=jwt_generation_failed")

    cb_param = f"&callbackUrl={quote(callback_url)}" if callback_url else ""
    return redirect(f"{frontend_url}/api/auth-exchange?token={internal_token}{cb_param}")


@auth_bp.route("/login", methods=["POST"])
def local_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Required"}), 400

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
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
    if db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none():
        return jsonify({"error": "Email already registered"}), 409

    # Create new user
    new_user = User(email=email, display_name=display_name, is_active=True)
    new_user.set_password(password)

    # Assign default 'user' role
    default_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
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


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log out the current user by revoking their token."""
    token = None
    if "Authorization" in request.headers:
        token = request.headers["Authorization"].split(" ")[1]
    elif "iqoqo_session" in request.cookies:
        token = request.cookies.get("iqoqo_session")

    if token:
        try:
            payload = pyjwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            jti = payload.get("jti")
            if jti:
                db.session.add(TokenBlocklist(jti=jti))
                db.session.commit()
        except IntegrityError:
            db.session.rollback()
            # Already revoked, treat as success (idempotent)
        except pyjwt.PyJWTError:
            pass  # Token is invalid or expired anyway

    return jsonify({"message": "Logged out successfully"}), 200
