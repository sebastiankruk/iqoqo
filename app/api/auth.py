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
import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, jsonify, redirect, request
from sqlalchemy.exc import IntegrityError

from app.db.models import Role, TokenBlocklist, User, db

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
    if app.config.get("APPLE_CLIENT_ID"):
        oauth.register(
            name="apple",
            client_id=app.config["APPLE_CLIENT_ID"],
            client_secret=None,  # Generated dynamically via JWT (client_secret_post)
            server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email name",
                "response_mode": "form_post",
            },
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
    """Initiate Google OAuth flow.

    When ``mobile_origin=capacitor`` is present, the login was initiated
    from the native Capacitor app.  In that case we use a dedicated mobile
    callback URL so the callback can always redirect to the ``iqoqo://``
    deep-link scheme – without relying on ``state`` (overwritten by
    authlib's CSRF token) or ``session`` (lost when the WebView opens
    Google in the system browser).
    """
    mobile_origin = request.args.get("mobile_origin")

    if mobile_origin == "capacitor":
        redirect_uri = request.url_root + "api/auth/callback/google/mobile"
    else:
        redirect_uri = request.url_root + "api/auth/callback/google"

    # Bulletproof Fail-safe: Force HTTPS in production/preview environments
    # just in case Nginx proxy headers strip the secure scheme.
    if redirect_uri.startswith("http://") and os.getenv("FLASK_ENV") == "production":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    return oauth.google.authorize_redirect(redirect_uri)


def _handle_google_user(token: dict) -> User:
    """Find or create a user from a Google OAuth token and return the User object.

    Shared by both the web and mobile Google callback routes.
    """
    user_info = oauth.google.parse_id_token(token, nonce=None)
    email = user_info.get("email")

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    picture = user_info.get("picture")

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
        # Optionally update avatar if it changed
        if picture and user.avatar_url != picture:
            user.avatar_url = picture

    user.last_login = datetime.now(UTC)
    db.session.commit()
    return user


@auth_bp.route("/callback/google")
def google_callback():
    """Handle Google OAuth callback for web logins."""
    token = oauth.google.authorize_access_token()
    user = _handle_google_user(token)
    internal_token = generate_internal_jwt(user)
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
    return redirect(f"{frontend_url}/auth-exchange?token={internal_token}")


@auth_bp.route("/callback/google/mobile")
def google_callback_mobile():
    """Handle Google OAuth callback for native Capacitor logins.

    Always redirects to the ``iqoqo://`` deep-link scheme so the native
    app can intercept the token.
    """
    token = oauth.google.authorize_access_token()
    user = _handle_google_user(token)
    internal_token = generate_internal_jwt(user)
    return redirect(f"iqoqo://auth-exchange?token={internal_token}")


@auth_bp.route("/login/apple")
def apple_login():
    """Initiate Sign in with Apple OAuth flow.

    Requires APPLE_CLIENT_ID to be configured.  Uses a dedicated mobile
    callback URL when ``mobile_origin=capacitor`` is present (same
    strategy as Google login — see ``google_login`` docstring).
    """
    if not current_app.config.get("APPLE_CLIENT_ID"):
        return jsonify({"error": "Apple Sign In is not configured on this instance."}), 503

    mobile_origin = request.args.get("mobile_origin")

    if mobile_origin == "capacitor":
        redirect_uri = request.url_root + "api/auth/callback/apple/mobile"
    else:
        redirect_uri = request.url_root + "api/auth/callback/apple"

    if redirect_uri.startswith("http://") and os.getenv("FLASK_ENV") == "production":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    return oauth.apple.authorize_redirect(redirect_uri)


def _handle_apple_user(token: dict) -> User | None:
    """Find or create a user from an Apple OAuth token.

    Returns the User object, or None if identification fails.
    Shared by both the web and mobile Apple callback routes.
    """
    user_info = oauth.apple.parse_id_token(token)

    apple_sub: str = user_info.get("sub", "")
    email: str | None = user_info.get("email")

    # Locate an existing user by Apple subject ID, then fall back to email.
    user = db.session.execute(db.select(User).filter_by(apple_id=apple_sub)).scalar_one_or_none()
    if not user and email:
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user:
            user.apple_id = apple_sub  # type: ignore[attr-defined]
        else:
            display_name = user_info.get("name") or (email.split("@")[0] if email else "User")
            user = User(
                email=email,
                apple_id=apple_sub,
                display_name=display_name,
                is_active=True,
            )
            default_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
            if default_role:
                user.roles.append(default_role)  # type: ignore[attr-defined]
            db.session.add(user)

    if user:
        user.last_login = datetime.now(UTC)
        db.session.commit()
    return user


@auth_bp.route("/callback/apple", methods=["POST"])
def apple_callback():
    """Handle Apple OAuth callback for web logins (form_post response mode)."""
    if not current_app.config.get("APPLE_CLIENT_ID"):
        return jsonify({"error": "Apple Sign In is not configured on this instance."}), 503

    token = oauth.apple.authorize_access_token()
    user = _handle_apple_user(token)
    if not user:
        return jsonify({"error": "Unable to identify user from Apple token."}), 400

    internal_token = generate_internal_jwt(user)
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
    return redirect(f"{frontend_url}/auth-exchange?token={internal_token}")


@auth_bp.route("/callback/apple/mobile", methods=["POST"])
def apple_callback_mobile():
    """Handle Apple OAuth callback for native Capacitor logins.

    Always redirects to the ``iqoqo://`` deep-link scheme.
    """
    if not current_app.config.get("APPLE_CLIENT_ID"):
        return jsonify({"error": "Apple Sign In is not configured on this instance."}), 503

    token = oauth.apple.authorize_access_token()
    user = _handle_apple_user(token)
    if not user:
        return jsonify({"error": "Unable to identify user from Apple token."}), 400

    internal_token = generate_internal_jwt(user)
    return redirect(f"iqoqo://auth-exchange?token={internal_token}")


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
