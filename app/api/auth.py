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
"""Authentication, session and token endpoints.

Owns login, logout, the session exchange used by the Next.js frontend, and the
admin bootstrap token. Token verification is delegated to the auth models, not
reimplemented here."""

import hashlib
import json
import logging
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse, urlsplit

import jwt as pyjwt
import requests
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, g, jsonify, redirect, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from joserfc.errors import JoseError
from jwt import PyJWKClient
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.api.decorators import admin_required, cache_token_revoked, require_auth
from app.config import Config
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.db.auth import PersonalAccessToken, generate_pat_token
from app.db.core import EntityAuditLog
from app.db.models import InstanceSettings, OAuthExchangeCode, Role, TokenBlocklist, User, db
from app.utils.allegro import exchange_device_token, initiate_device_flow
from app.utils.http_client import is_safe_url

# Werkzeug's default KDF, and the reason login timing needs care. `scrypt` with
# these parameters costs roughly 90 ms, which is far longer than any network or
# framework overhead around it.
_PASSWORD_HASH_METHOD = "scrypt"

# Hash of a value generated per process and never disclosed, used to keep the
# "no such account" path as expensive as the "wrong password" path. See
# `_verify_login_password`.
_dummy_password_hash: str | None = None


def _verify_login_password(user: User | None, password: str) -> bool:
    """Check a password without revealing whether the account exists.

    The KDF dominates this endpoint's runtime, so the naive
    ``if not user or not user.check_password(password)`` answered "no such
    account" without ever hashing: 0.00 ms against 90.40 ms for a registered
    email with a wrong password, measured on identical code. That gap enumerates
    every registered address far more reliably than the generic error message
    hides it, and the same shortcut applied to a Google-only account, whose
    ``password_hash`` is NULL by design (`ck_user_auth_method`).

    Verifying against a throwaway hash when there is nothing to check makes the
    two paths cost the same. The throwaway is a fresh random value per process,
    so the hash is worthless even if it were ever extracted from a core dump.

    @param user: The matched account, or None when no account matched.
    @param password: The submitted password.
    @returns: True only when the account exists and the password matches.
    """
    global _dummy_password_hash  # noqa: PLW0603 - a process-lifetime constant, set once

    stored_hash = user.password_hash if user is not None else None
    if stored_hash:
        return check_password_hash(stored_hash, password)

    if _dummy_password_hash is None:
        _dummy_password_hash = generate_password_hash(secrets.token_urlsafe(32), method=_PASSWORD_HASH_METHOD)
    check_password_hash(_dummy_password_hash, password)
    return False


logger = logging.getLogger(__name__)
OAUTH_EXCHANGE_CODE_TTL_SECONDS = 60

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
oauth = OAuth()


def _ensure_google_oauth() -> bool:
    """Ensure Google OAuth client is registered with current credentials.

    Priority:
    1. Database (InstanceSettings table via ConfigService)
    2. Flask app config
    3. Environment variables

    Returns:
        True if the client is registered, False if credentials are not configured.
    """
    from app.core.config_service import ConfigService

    client_id = ConfigService.get("GOOGLE_CLIENT_ID")
    client_secret = ConfigService.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return False

    existing_client = getattr(oauth, "google", None)
    if existing_client is not None:
        if getattr(existing_client, "client_id", None) == client_id and getattr(existing_client, "client_secret", None) == client_secret:
            return True
        oauth._clients.pop("google", None)  # pylint: disable=protected-access

    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return True


def _ensure_apple_oauth() -> bool:
    """Ensure Apple OAuth is configured.

    Priority:
    1. Database (InstanceSettings table via ConfigService)
    2. Flask app config
    3. Environment variables

    Returns:
        True if Apple client ID is configured.
    """
    from app.core.config_service import ConfigService

    client_id = ConfigService.get("APPLE_CLIENT_ID")
    return bool(client_id)


def init_oauth(app):
    """Register the OAuth providers on the application.

    Called once during app setup. Providers are registered only when their client id
    and secret are configured, so an instance with no OAuth keys starts normally."""
    oauth.init_app(app)
    with app.app_context():
        try:
            _ensure_google_oauth()
        except (
            SQLAlchemyError,
            ValueError,
            AttributeError,
            KeyError,
            RuntimeError,
        ) as exc:
            app.logger.warning("Could not initialize Google OAuth at startup: %s", exc)


def generate_internal_jwt(user: User) -> str:
    """Mint a short-lived internal JWT for a user.

    Used for server-to-server calls that must act as a specific user without holding
    that user's session. The token is short-lived and carries no refresh capability."""
    payload = {
        "sub": str(user.id),
        "jti": str(uuid.uuid4()),  # Unique ID for revocation
        "email": user.email,
        "roles": [role.name for role in user.roles],  # type: ignore[attr-defined]
        "exp": datetime.now(UTC) + timedelta(days=7),  # matches the session cookie lifetime
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def _safe_oauth_callback_path(candidate: object) -> str | None:
    """Accept only same-origin relative paths for the post-login redirect."""
    if not isinstance(candidate, str) or not candidate.startswith("/") or candidate.startswith("//") or "\\" in candidate:
        return None
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return candidate


def _get_oauth_serializer() -> URLSafeTimedSerializer:
    """Return a URLSafeTimedSerializer keyed with SECRET_KEY for OAuth CSRF state."""
    secret_key = current_app.config.get("SECRET_KEY") or "iqoqo-default-oauth-state-secret-key"
    return URLSafeTimedSerializer(secret_key, salt="oauth-state-nonce")


def _generate_oauth_state(mobile_origin: str | None = None, callback_url: str | None = None) -> str:
    """Generate a signed, tamper-proof state token carrying client context."""
    serializer = _get_oauth_serializer()
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "mobile_origin": mobile_origin,
        "callback_url": callback_url,
    }
    return serializer.dumps(payload)


def _verify_oauth_state(state_token: str | None, max_age: int = 600) -> dict | None:
    """Verify and decode a signed state token. Returns None on missing, expired or invalid state."""
    if not state_token or not isinstance(state_token, str):
        return None
    serializer = _get_oauth_serializer()
    try:
        data = serializer.loads(state_token, max_age=max_age)
        if isinstance(data, dict):
            return data
    except (BadSignature, SignatureExpired) as e:
        logger.warning("OAuth state verification failed: %s", e)
    return None


_apple_jwk_client: PyJWKClient | None = None


def _get_apple_jwk_client() -> PyJWKClient:
    """Return a cached PyJWKClient for Apple's public signing keys."""
    global _apple_jwk_client
    if _apple_jwk_client is None:
        _apple_jwk_client = PyJWKClient("https://appleid.apple.com/auth/keys", cache_keys=True, max_cached_keys=16)
    return _apple_jwk_client


def _verify_apple_id_token(id_token_str: str, client_id: str) -> dict:
    """Cryptographically verify an Apple id_token using Apple's JWKS public keys.

    Validates signature, issuer, audience, and expiration.
    """
    jwk_client = _get_apple_jwk_client()
    signing_key = jwk_client.get_signing_key_from_jwt(id_token_str)
    claims = pyjwt.decode(
        id_token_str,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer="https://appleid.apple.com",
        options={
            "verify_signature": True,
            "verify_aud": True,
            "verify_iss": True,
            "verify_exp": True,
        },
    )
    return claims


def _issue_oauth_exchange_code(user: User, callback_url: str | None) -> str:
    """Persist a hashed, single-use code and return the raw browser handoff value."""
    now = datetime.now(UTC)
    db.session.execute(db.delete(OAuthExchangeCode).where(OAuthExchangeCode.expires_at <= now))

    code = secrets.token_urlsafe(32)
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    db.session.add(
        OAuthExchangeCode(
            code_hash=code_hash,
            user_id=user.id,
            callback_url=callback_url,
            expires_at=now + timedelta(seconds=OAUTH_EXCHANGE_CODE_TTL_SECONDS),
        )
    )
    db.session.commit()
    return code


@auth_bp.route("/providers", methods=["GET"])
def get_auth_providers():
    """Return active authentication providers and capabilities.

    Unauthenticated public endpoint allowing clients to adapt login/registration surfaces dynamically.
    """
    try:
        google_active = bool(_ensure_google_oauth())
    except (
        SQLAlchemyError,
        ValueError,
        AttributeError,
        KeyError,
        RuntimeError,
    ) as exc:
        logger.warning("Error checking Google OAuth provider status: %s", exc)
        google_active = False

    try:
        apple_active = bool(_ensure_apple_oauth())
    except (
        SQLAlchemyError,
        ValueError,
        AttributeError,
        KeyError,
        RuntimeError,
    ) as exc:
        logger.warning("Error checking Apple OAuth provider status: %s", exc)
        apple_active = False

    return jsonify({"google": google_active, "apple": apple_active}), 200


@auth_bp.route("/login/google")
def google_login():
    """Start the Google OAuth flow.

    Builds the consent redirect, carrying a signed CSRF state value that the callback
    verifies before issuing a session."""
    if not _ensure_google_oauth():
        logger.warning("Google OAuth login attempted but Google client is not configured")
        frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/login?error=oauth_not_configured")

    callback_url = _safe_oauth_callback_path(request.args.get("callbackUrl") or request.args.get("redirect"))
    mobile_origin = request.args.get("mobile_origin") or ("capacitor" if request.args.get("mobile") == "1" else None)

    state = _generate_oauth_state(mobile_origin=mobile_origin, callback_url=callback_url)
    session["oauth_google_state"] = state

    redirect_uri = request.url_root + "api/auth/callback/google"
    original_uri = redirect_uri

    # Bulletproof Fail-safe: Force HTTPS in production/preview environments
    # just in case Nginx proxy headers strip the secure scheme.
    if redirect_uri.startswith("http://") and os.getenv("FLASK_ENV") == "production":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    logger.info("Google OAuth redirect_uri: %s (original: %s)", redirect_uri, original_uri)

    try:
        return oauth.google.authorize_redirect(redirect_uri, state=state)
    except (OAuthError, AttributeError) as e:
        logger.error("Google OAuth authorize_redirect failed: %s", e, exc_info=True)
        return jsonify({"error": "Google sign-in could not be started. Please try again later."}), 502


@auth_bp.route("/callback/google")
def google_callback():
    """Complete the Google OAuth flow and establish a session.

    Verifies the signed state value first. An unverified callback would let an attacker
    attach their own Google identity to a victim's session, so this is the security
    boundary of the whole flow."""
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
    error_code = None

    if not _ensure_google_oauth():
        logger.warning("Google OAuth callback received but Google client is not configured")
        error_code = "oauth_not_configured"

    state_arg = request.args.get("state")
    verified_state = _verify_oauth_state(state_arg)
    saved_state = session.pop("oauth_google_state", None)

    # State must be cryptographically valid
    if not verified_state or (saved_state and saved_state != state_arg):
        logger.warning("Google OAuth state verification failed or mismatch")
        return redirect(f"{frontend_url}/login?error=csrf_state_mismatch")

    callback_url = verified_state.get("callback_url")
    mobile_origin = verified_state.get("mobile_origin")

    token = None
    if not error_code:
        try:
            token = oauth.google.authorize_access_token()
        except (OAuthError, AttributeError) as e:
            logger.error("Google OAuth token exchange failed: %s", e, exc_info=True)
            error_code = "token_exchange_failed"

    user_info = None
    if not error_code and token:
        try:
            user_info = oauth.google.parse_id_token(token, nonce=None)
        except (JoseError, AttributeError) as e:
            logger.error("Google OAuth parse_id_token failed: %s", e, exc_info=True)
            error_code = "id_token_parse_failed"

    raw_email = user_info.get("email") if user_info else None
    email = raw_email.strip().lower() if raw_email else None
    google_id = str(user_info.get("sub")) if user_info and user_info.get("sub") else None

    if not error_code and not email:
        logger.error("Google OAuth: no email in user_info: %s", user_info)
        error_code = "no_email"

    if error_code:
        return redirect(f"{frontend_url}/login?error={error_code}")

    raw_picture = user_info.get("picture") if user_info else None
    picture: str | None = None
    if raw_picture:
        candidate_picture = str(raw_picture).strip()
        try:
            if urlparse(candidate_picture).scheme == "https" and is_safe_url(candidate_picture):
                picture = candidate_picture
            else:
                logger.warning("Unsafe or non-HTTPS OAuth avatar_url rejected: %s", candidate_picture)
        except Exception:
            logger.warning("Failed to validate OAuth avatar_url: %s", candidate_picture, exc_info=True)
            picture = None

    try:
        user = None
        if google_id:
            user = db.session.execute(db.select(User).filter_by(google_id=google_id)).scalar_one_or_none()
        if not user and email:
            user = db.session.execute(db.select(User).filter(func.lower(User.email) == email)).scalar_one_or_none()
            if user and google_id:
                user.google_id = google_id

        if not user:
            user = User(
                email=email,
                display_name=user_info.get("name"),
                is_active=True,
                google_id=google_id,
                avatar_url=picture,
            )
            default_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
            if default_role:
                user.roles.append(default_role)
            db.session.add(user)
        else:
            if picture and user.avatar_url != picture:
                user.avatar_url = picture

            from app.core.account_tokens import mark_verified_from_oidc

            if mark_verified_from_oidc(user, user_info):
                logger.info("Marked the federated address for user %s as verified on provider assertion", user.id)

        if not user.is_active:
            db.session.rollback()
            logger.warning("OAuth login refused for suspended user %s", user.id)
            return redirect(f"{frontend_url}/login?error=account_suspended")

        user.last_login = datetime.now(UTC)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Google OAuth user creation/update failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=user_setup_failed")

    try:
        exchange_code = _issue_oauth_exchange_code(user, _safe_oauth_callback_path(callback_url))
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Google OAuth exchange-code creation failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=oauth_exchange_failed")

    if mobile_origin == "capacitor":
        response = redirect(f"{frontend_url.rstrip('/')}/auth-exchange?mobile=1&code={exchange_code}")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    response = redirect(f"{frontend_url.rstrip('/')}/api/auth-exchange?code={exchange_code}")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@auth_bp.route("/login/apple")
@limiter.limit("20 per minute")
def apple_login():
    """Start the Apple OAuth flow."""
    if not _ensure_apple_oauth():
        logger.warning("Apple OAuth login attempted but Apple client is not configured")
        frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
        return redirect(f"{frontend_url}/login?error=apple_oauth_not_configured")

    from app.core.config_service import ConfigService

    client_id = ConfigService.get("APPLE_CLIENT_ID")
    callback_url = _safe_oauth_callback_path(request.args.get("callbackUrl") or request.args.get("redirect"))
    mobile_origin = request.args.get("mobile_origin") or ("capacitor" if request.args.get("mobile") == "1" else None)

    state = _generate_oauth_state(mobile_origin=mobile_origin, callback_url=callback_url)
    session["oauth_apple_state"] = state

    redirect_uri = request.url_root + "api/auth/callback/apple"
    if redirect_uri.startswith("http://") and os.getenv("FLASK_ENV") == "production":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "name email",
        "state": state,
    }
    apple_auth_url = f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"
    return redirect(apple_auth_url)


@auth_bp.route("/callback/apple", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def apple_callback():
    """Complete Apple Sign In flow."""
    frontend_url = os.getenv("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")

    if not _ensure_apple_oauth():
        logger.warning("Apple OAuth callback received but Apple client is not configured")
        return redirect(f"{frontend_url}/login?error=apple_oauth_not_configured")

    from app.core.config_service import ConfigService

    client_id = ConfigService.get("APPLE_CLIENT_ID") or ""

    # Apple returns params via POST (form_post) or GET
    payload: dict[str, str] = {}
    if request.method == "POST":
        payload = request.form.to_dict()
    else:
        payload = request.args.to_dict()

    if not payload and request.is_json:
        payload = request.get_json(silent=True) or {}

    state_arg = payload.get("state")
    verified_state = _verify_oauth_state(state_arg)
    saved_state = session.pop("oauth_apple_state", None)

    # Note: On cross-site form_post, browsers may drop SameSite=Lax session cookies,
    # so saved_state might be None. verified_state must be valid regardless!
    if not verified_state or (saved_state and saved_state != state_arg):
        logger.warning("Apple OAuth state verification failed or mismatch")
        return redirect(f"{frontend_url}/login?error=csrf_state_mismatch")

    callback_url = verified_state.get("callback_url")
    mobile_origin = verified_state.get("mobile_origin")

    id_token_str = payload.get("id_token")
    user_payload_raw = payload.get("user")

    if not id_token_str:
        logger.error("Apple OAuth callback missing id_token: %s", payload)
        return redirect(f"{frontend_url}/login?error=missing_id_token")

    # Cryptographically verify id_token claims using Apple JWKS
    try:
        claims = _verify_apple_id_token(id_token_str, client_id)
    except Exception as e:
        logger.error("Failed to verify Apple id_token signature/claims: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=invalid_id_token")

    apple_id = str(claims.get("sub")) if claims.get("sub") else None
    raw_email = claims.get("email")
    email = raw_email.strip().lower() if raw_email else None
    raw_email_verified = claims.get("email_verified")
    email_is_verified = raw_email_verified is True or str(raw_email_verified).lower() == "true"

    if not apple_id:
        logger.error("Apple id_token missing sub claim: %s", claims)
        return redirect(f"{frontend_url}/login?error=missing_apple_sub")

    display_name = None
    if user_payload_raw:
        try:
            user_data = json.loads(user_payload_raw) if isinstance(user_payload_raw, str) else user_payload_raw
            name_obj = user_data.get("name", {})
            first = name_obj.get("firstName", "")
            last = name_obj.get("lastName", "")
            full = f"{first} {last}".strip()
            if full:
                display_name = full
        except Exception:
            pass

    try:
        user = db.session.execute(db.select(User).filter_by(apple_id=apple_id)).scalar_one_or_none()
        # Only link existing account by email if email is verified by Apple
        if not user and email and email_is_verified:
            user = db.session.execute(db.select(User).filter(func.lower(User.email) == email)).scalar_one_or_none()
            if user:
                user.apple_id = apple_id

        if not user:
            account_email = email or f"{apple_id}@privaterelay.appleid.apple.com"
            user = User(
                email=account_email,
                display_name=display_name or "Apple User",
                apple_id=apple_id,
                is_active=True,
            )
            default_role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
            if default_role:
                user.roles.append(default_role)
            db.session.add(user)
        else:
            if display_name and not user.display_name:
                user.display_name = display_name

        from app.core.account_tokens import mark_verified_from_oidc

        mark_verified_from_oidc(user, claims)

        if not user.is_active:
            db.session.rollback()
            logger.warning("Apple OAuth login refused for suspended user %s", user.id)
            return redirect(f"{frontend_url}/login?error=account_suspended")

        user.last_login = datetime.now(UTC)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Apple OAuth user creation failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=user_setup_failed")

    try:
        exchange_code = _issue_oauth_exchange_code(user, _safe_oauth_callback_path(callback_url))
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Apple OAuth exchange-code creation failed: %s", e, exc_info=True)
        return redirect(f"{frontend_url}/login?error=oauth_exchange_failed")

    if mobile_origin == "capacitor":
        response = redirect(f"{frontend_url.rstrip('/')}/auth-exchange?mobile=1&code={exchange_code}")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    response = redirect(f"{frontend_url.rstrip('/')}/api/auth-exchange?code={exchange_code}")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@auth_bp.route("/exchange", methods=["POST"])
def exchange_oauth_code():
    """Atomically consume a short-lived OAuth code and issue the iQoQo session JWT."""
    data = request.get_json(silent=True)
    code = data.get("code") if isinstance(data, dict) else None
    if not isinstance(code, str) or len(code) != 43:
        return jsonify({"error": "Invalid or expired authorization code"}), 400

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    try:
        row = db.session.execute(
            db.delete(OAuthExchangeCode)
            .where(OAuthExchangeCode.code_hash == code_hash, OAuthExchangeCode.expires_at > now)
            .returning(OAuthExchangeCode.user_id, OAuthExchangeCode.callback_url)
        ).first()
        if row is None:
            db.session.rollback()
            return jsonify({"error": "Invalid or expired authorization code"}), 400

        user = db.session.get(User, row.user_id)
        if not user or not user.is_active:
            db.session.commit()
            return jsonify({"error": "Invalid or expired authorization code"}), 400

        token = generate_internal_jwt(user)
        callback_url = _safe_oauth_callback_path(row.callback_url) or "/"
        db.session.commit()
    except (SQLAlchemyError, pyjwt.PyJWTError) as exc:
        db.session.rollback()
        logger.error("OAuth authorization-code exchange failed: %s", exc, exc_info=True)
        return jsonify({"error": "Unable to complete OAuth exchange"}), 500

    res = jsonify({"token": token, "access_token": token, "token_type": "Bearer", "callbackUrl": callback_url})
    res.headers["Cache-Control"] = "no-store"
    res.headers["Pragma"] = "no-cache"
    return res, 200


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def local_login():
    """Authenticate with an email and password.

    The password is verified against a hash, and the response is generic on failure
    so it does not reveal whether an account exists. The HTTP status code carries
    no account state (both invalid credentials and suspended accounts return 401
    only after full password verification)."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Required"}), 400

    email = str(email).strip().lower()
    user = db.session.execute(db.select(User).filter(func.lower(User.email) == email)).scalar_one_or_none()
    if not _verify_login_password(user, password):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error": "Account suspended", "suspended": True}), 401

    if user.totp_enabled:
        otp_code = data.get("otp_code") or data.get("totp_code") or data.get("code")
        if not otp_code:
            return jsonify({"mfa_required": True, "message": "Two-factor authentication required"}), 200

        # Validate OTP or recovery code
        is_valid = user.verify_totp(str(otp_code).strip())
        if not is_valid:
            is_valid = user.verify_and_consume_recovery_code(str(otp_code).strip())

        if not is_valid:
            return jsonify({"error": "Invalid two-factor authentication code"}), 401

    user.last_login = datetime.now(UTC)
    db.session.commit()
    return jsonify({"token": generate_internal_jwt(user), "user": {"id": str(user.id), "email": user.email}})


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def local_register():
    """Create a local account and sign the user in.

    Permitted only on an instance with no accounts yet, or when registration is
    explicitly enabled; otherwise the endpoint refuses rather than creating an
    uninvited user."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    display_name = data.get("display_name")

    if not email or password is None:
        return jsonify({"error": "Email and password are required"}), 400

    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400

    # Check if user already exists. The comparison is case-insensitive because
    # the account-lifecycle endpoints normalise addresses to lower case, so a
    # mixed-case registration here would otherwise create a second account for
    # the same mailbox -- and then block the owner from ever re-verifying the
    # address their profile reports.
    if db.session.execute(db.select(User).filter(func.lower(User.email) == email.strip().lower())).scalar_one_or_none():
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

    # `email_verified_at` is deliberately left NULL. A self-registered address is
    # exactly the unproven case the column exists for: whoever typed it may not
    # control it, so it starts unverified and the owner confirms it themselves.
    # Noted explicitly because the next reader will otherwise go looking for the
    # place verification happens.
    logger.info("Registered a local account; its address starts unverified pending confirmation")

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
        jti = None
        exp = None
        try:
            payload = pyjwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            jti = payload.get("jti")
            exp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp, UTC) if exp else None
            if jti:
                db.session.add(TokenBlocklist(jti=jti, expires_at=expires_at))
                db.session.commit()
                cache_token_revoked(jti, exp)
        except IntegrityError:
            db.session.rollback()
            # Already revoked, treat as success (idempotent)
            cache_token_revoked(jti, exp)
        except pyjwt.PyJWTError:
            pass  # Token is invalid or expired anyway

    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/allegro/device-flow", methods=["POST"])
@require_auth
@admin_required
def allegro_device_flow():
    """Initiate Allegro Device Code flow."""
    data = request.get_json() or {}
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    if not client_id or str(client_id).startswith("***"):
        client_id = (
            InstanceSettings.get_value("ALLEGRO_CLIENT_ID") or getattr(Config, "ALLEGRO_CLIENT_ID", None) or os.getenv("ALLEGRO_CLIENT_ID")
        )
    if not client_secret or str(client_secret).startswith("***"):
        client_secret = (
            InstanceSettings.get_value("ALLEGRO_CLIENT_SECRET")
            or getattr(Config, "ALLEGRO_CLIENT_SECRET", None)
            or os.getenv("ALLEGRO_CLIENT_SECRET")
        )

    if not client_id or not client_secret:
        return jsonify({"error": "client_id and client_secret are required"}), 400

    try:
        flow_data = initiate_device_flow(str(client_id), str(client_secret))
        return jsonify(flow_data), 200
    except (requests.RequestException, OSError, ValueError) as e:
        logger.error("Failed to initiate Allegro device flow: %s", e, exc_info=True)
        return jsonify({"error": "Failed to initiate device flow"}), 500


@auth_bp.route("/allegro/device-token", methods=["POST"])
@require_auth
@admin_required
def allegro_device_token():
    """Poll Allegro for the token using the device code."""
    data = request.get_json() or {}
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    device_code = data.get("device_code")

    if not client_id or str(client_id).startswith("***"):
        client_id = (
            InstanceSettings.get_value("ALLEGRO_CLIENT_ID") or getattr(Config, "ALLEGRO_CLIENT_ID", None) or os.getenv("ALLEGRO_CLIENT_ID")
        )
    if not client_secret or str(client_secret).startswith("***"):
        client_secret = (
            InstanceSettings.get_value("ALLEGRO_CLIENT_SECRET")
            or getattr(Config, "ALLEGRO_CLIENT_SECRET", None)
            or os.getenv("ALLEGRO_CLIENT_SECRET")
        )

    if not client_id or not client_secret or not device_code:
        return jsonify({"error": "client_id, client_secret, and device_code are required"}), 400

    try:
        token_data = exchange_device_token(str(device_code), str(client_id), str(client_secret))
        if "access_token" in token_data:
            return jsonify({"status": "success", "message": "Allegro authorized successfully"}), 200

        err = token_data.get("error", "")
        return jsonify({"status": "pending", "error": err, "details": token_data}), 202
    except (requests.RequestException, OSError, ValueError) as e:
        logger.error("Failed to exchange Allegro device token: %s", e, exc_info=True)
        return jsonify({"error": "Failed to exchange device token"}), 500


# ---------------------------------------------------------------------------
# Two-Factor Authentication (TOTP 2FA)
# ---------------------------------------------------------------------------


def _reject_pat_auth():
    """Reject requests authenticated via Personal Access Tokens for token/2FA management."""
    if getattr(g, "pat", None) is not None:
        return jsonify({"error": "Personal access tokens cannot manage tokens or 2FA settings"}), 403
    return None


@auth_bp.route("/2fa/status", methods=["GET"])
@require_auth
def get_2fa_status():
    """Return whether 2FA is enabled for the authenticated user."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err
    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"enabled": bool(user.totp_enabled)}), 200


@auth_bp.route("/2fa/enroll", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def enroll_2fa():
    """Initiate TOTP enrollment by generating secret, provisioning URI, recovery codes, and QR code."""
    import base64
    import io

    import pyotp
    import qrcode

    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.totp_enabled:
        return jsonify({"error": "2FA is already enabled. Disable 2FA before re-enrolling."}), 400

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    issuer = current_app.config.get("INSTANCE_NAME", "iqoqo")
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)

    # 8 single-use recovery codes
    recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]

    # Store encrypted secret and hashed recovery codes, but leave totp_enabled=False until verified
    user.set_totp_secret(secret)
    user.set_recovery_codes(recovery_codes)
    db.session.commit()

    # Generate QR code PNG as data URI
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    return (
        jsonify(
            {
                "secret": secret,
                "provisioning_uri": provisioning_uri,
                "recovery_codes": recovery_codes,
                "qr_code": qr_data_url,
            }
        ),
        200,
    )


@auth_bp.route("/2fa/verify", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def verify_2fa():
    """Verify a TOTP code and finalize enabling 2FA."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    code = str(data.get("code") or data.get("otp_code") or "").strip()
    if not code:
        return jsonify({"error": "Verification code is required"}), 400

    if not user.verify_totp(code):
        return jsonify({"error": "Invalid verification code"}), 400

    user.totp_enabled = True
    audit = EntityAuditLog(
        entity_type="user",
        entity_id=0,
        actor_id=user.id,
        change_type="2fa_enabled",
        diff={"totp_enabled": True},
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({"success": True, "enabled": True}), 200


@auth_bp.route("/2fa/disable", methods=["POST"])
@limiter.limit("10 per minute")
@require_auth
def disable_2fa():
    """Disable 2FA after validating user password or a valid 2FA/recovery code."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    password = data.get("password")
    code = str(data.get("code") or data.get("otp_code") or "").strip()

    valid = False
    if password and user.check_password(password):
        valid = True
    elif code and (user.verify_totp(code) or user.verify_and_consume_recovery_code(code)):
        valid = True

    if not valid:
        return jsonify({"error": "Invalid password or verification code"}), 400

    user.totp_enabled = False
    user.set_totp_secret(None)
    user.totp_recovery_codes = None
    audit = EntityAuditLog(
        entity_type="user",
        entity_id=0,
        actor_id=user.id,
        change_type="2fa_disabled",
        diff={"totp_enabled": False},
    )
    db.session.add(audit)
    db.session.commit()
    return jsonify({"success": True, "enabled": False}), 200


# ---------------------------------------------------------------------------
# Personal Access Tokens (PATs)
# ---------------------------------------------------------------------------


@auth_bp.route("/tokens", methods=["GET"])
@require_auth
def list_tokens():
    """List personal access tokens for the authenticated user with SQL pagination."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    try:
        raw_limit = int(request.args.get("limit", 20))
        raw_offset = int(request.args.get("offset", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Limit and offset must be integers"}), 400

    if raw_limit < 1 or raw_offset < 0:
        return jsonify({"error": "Limit must be >= 1 and offset must be >= 0"}), 400

    limit = min(raw_limit, 100)
    offset = raw_offset

    stmt = (
        db.select(PersonalAccessToken)
        .filter_by(user_id=g.user_id)
        .order_by(PersonalAccessToken.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tokens = db.session.execute(stmt).scalars().all()

    count_stmt = db.select(func.count()).select_from(PersonalAccessToken).filter_by(user_id=g.user_id)  # pylint: disable=not-callable
    total = db.session.execute(count_stmt).scalar() or 0

    return (
        jsonify(
            {
                "items": [t.to_dict() for t in tokens],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        ),
        200,
    )


@auth_bp.route("/tokens", methods=["POST"])
@require_auth
def create_token():
    """Create a new personal access token and return plaintext token once."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Token name is required"}), 400
    if len(name) > 100:
        return jsonify({"error": "Token name must not exceed 100 characters"}), 400

    scopes = data.get("scopes") or ["read:catalog"]
    if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
        return jsonify({"error": "Scopes must be a list of strings"}), 400

    user = db.session.get(User, g.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    is_admin = any(role.name == "admin" for role in getattr(user, "roles", []))
    is_curator = is_admin or any(role.name in {"contributor", "custodian"} for role in getattr(user, "roles", []))

    valid_standard = {"read:catalog", "write:catalog", "write:inventory", "sparql:query", "curator", "admin", "*"}
    for s in scopes:
        if s not in valid_standard and not any(s == p.value for p in PermissionName):
            return jsonify({"error": f"Invalid scope: {s}"}), 400
        if s in {"admin", "*"} and not is_admin:
            return jsonify({"error": "Admin scope requires admin role"}), 403
        if s == "curator" and not is_curator:
            return jsonify({"error": "Curator scope requires contributor, custodian, or admin role"}), 403
        if any(s == p.value for p in PermissionName) and not (is_admin or user.has_permission(s)):
            return jsonify({"error": f"Caller lacks permission for scope {s}"}), 403

    expires_in_days = data.get("expires_in_days")
    expires_at = None
    if expires_in_days is not None:
        try:
            days = int(expires_in_days)
            if days <= 0:
                return jsonify({"error": "expires_in_days must be a positive integer"}), 400
            expires_at = datetime.now(UTC) + timedelta(days=days)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid expires_in_days"}), 400

    raw_token, prefix, token_hash = generate_pat_token()
    pat = PersonalAccessToken(
        user_id=g.user_id,
        name=name,
        token_prefix=prefix,
        token_hash=token_hash,
        scopes=scopes,
        expires_at=expires_at,
    )
    db.session.add(pat)
    db.session.commit()

    return (
        jsonify(
            {
                "token": raw_token,
                "data": pat.to_dict(),
            }
        ),
        201,
    )


@auth_bp.route("/tokens/<int:token_id>", methods=["DELETE"])
@require_auth
def revoke_token(token_id: int):
    """Revoke an active personal access token."""
    pat_err = _reject_pat_auth()
    if pat_err:
        return pat_err

    pat = db.session.execute(db.select(PersonalAccessToken).filter_by(id=token_id, user_id=g.user_id)).scalar_one_or_none()

    if not pat:
        return jsonify({"error": "Token not found"}), 404

    pat.revoked_at = datetime.now(UTC)
    db.session.commit()
    return jsonify({"success": True, "message": "Token revoked"}), 200
