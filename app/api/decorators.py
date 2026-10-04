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
"""Shared route decorators: authentication, RBAC, rate limiting.

The permission decorator resolves the caller's role to a permission set and
denies by default. It is deliberately the only supported way to expose an
authenticated route, so an endpoint cannot accidentally ship without a check."""

import hashlib
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

#: Response for every credential that is cryptographically valid but belongs to
#: an account that no longer exists or has been suspended.
#:
#: Deliberately identical to the invalid-token response.  A distinct 403 here
#: would be an oracle: an attacker holding a stolen or expired token could tell
#: "this account is gone" from "this account is fine, your token is not", which
#: is both an enumeration channel and a way to confirm a successful deletion.
_CREDENTIAL_NO_LONGER_VALID = {"error": "Invalid token"}


def _extract_bearer_token() -> tuple[str | None, bool]:
    """Return the presented credential and whether cookie auth was in use.

    The boolean drives CSRF enforcement: a header credential is not attached by
    the browser automatically, so cross-site forgery does not apply to it, while
    a cookie credential is.

    Parsing is strict on purpose.  ``"Bearer"`` with no value used to raise
    ``IndexError`` and return a 500, which tells an attacker the endpoint exists
    and differs from a merely-malformed header.

    Args:
        None.

    Returns:
        ``(token, from_cookie)``.  ``token`` is None when no usable credential
        was presented; ``from_cookie`` is False in that case.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is not None:
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            return None, False
        return parts[1].strip(), False
    cookie = request.cookies.get("iqoqo_session")
    if cookie:
        return cookie, True
    return None, False


def _account_is_usable(user_id: uuid.UUID) -> bool:
    """Whether the account behind *user_id* may still act.

    A JWT is a bearer credential with a seven-day life and no server-side
    record, so without this check a deleted account's tokens kept working until
    they expired -- and the per-token blocklist cannot help, because it only
    knows about tokens someone explicitly logged out of.  Deleting an account
    has to invalidate every credential ever issued for it, and a stateless token
    has no version field to compare, so the only place to check is the account
    row itself.

    The lookup is deliberately **not** cached.  A cached "account is active"
    answer would keep a suspended or deleted account usable for the length of
    the TTL, which is the exact window the check exists to close.  SQLAlchemy's
    identity map absorbs the cost within a request: a route that checks twice
    still issues one query.

    Args:
        user_id: The subject claim of the presented token.

    Returns:
        True when the account exists and is active.
    """
    try:
        user = db.session.get(User, user_id)
    except Exception:
        # A database blip must not authenticate anyone.  Failing closed here is
        # the difference between a degraded read and an open door.
        db.session.rollback()
        logger.error("Account lookup failed while authenticating a request", exc_info=True)
        return False
    return user is not None and bool(user.is_active)



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
    """Reject the request unless a valid credential for a live account is present.

    Accepts a bearer token first and falls back to the session cookie, so the same
    decorator serves both the API clients and the server-rendered frontend.

    This is the only supported way to expose an authenticated route: a view that
    omits it is unprotected, and the permission decorator composes on top of it.

    Three things are checked, in order: the signature and expiry, the per-token
    revocation blocklist, and whether the account behind the token still exists
    and is active.  The third is what makes account deletion and suspension
    actually revoke credentials -- see :func:`_account_is_usable`."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token, from_cookie = _extract_bearer_token()

        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

            # Check blocklist
            if _is_token_revoked(payload.get("jti"), payload.get("exp")):
                return jsonify({"error": "Token revoked"}), 401

            user_id = uuid.UUID(payload["sub"])

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        except (ValueError, KeyError, TypeError):
            # Catches a `sub` that is not a UUID string, is absent, or is not a
            # string at all. All three are malformed credentials, not bugs.
            return jsonify({"error": "Invalid token"}), 401

        if not _account_is_usable(user_id):
            return jsonify(_CREDENTIAL_NO_LONGER_VALID), 401

        g.user_id = user_id
        g.authenticated_via_cookie = from_cookie
        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    """Attach the caller when a credential is present, without requiring one.

    Used for endpoints whose response varies for a signed-in user but is valid
    anonymously, such as public profile views.

    Applies the same live-account check as :func:`require_auth`: a token for a
    deleted or suspended account is treated as no token at all, rather than as a
    valid identity that happens to have no permissions.  Without that, a deleted
    account's outstanding JWT would still shape the response of every endpoint
    that decorates with this."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token, from_cookie = _extract_bearer_token()

        g.user_id = None
        g.authenticated_via_cookie = False
        if token:
            try:
                payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
                if not _is_token_revoked(payload.get("jti"), payload.get("exp")):
                    candidate = uuid.UUID(payload["sub"])
                    if _account_is_usable(candidate):
                        g.user_id = candidate
                        g.authenticated_via_cookie = from_cookie
            except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, jwt.DecodeError, KeyError, ValueError, TypeError):
                pass

        return f(*args, **kwargs)

    return decorated


def require_csrf(f):
    """Require a valid CSRF proof, but only for cookie-authenticated requests.

    Cross-site request forgery needs the browser to attach the credential by
    itself, which only a cookie does -- a header credential is not added
    automatically, so demanding CSRF proof for those would protect against
    nothing while breaking every API client and the Playwright suite.

    Skipping bearer requests must be done by *reading how the caller
    authenticated*, never by reading whether the header happens to be present:
    a request can carry both, and only the precedence in
    :func:`_extract_bearer_token` decides which one was actually used.

    The proof is a signed double-submit token.  Signing is what makes this
    robust: without it, anyone able to set a cookie for the domain -- through a
    sibling subdomain, or a plain-HTTP request during the redirect to HTTPS --
    could plant their own value and satisfy the comparison.  The HMAC means a
    planted cookie cannot produce a valid token.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(g, "authenticated_via_cookie", False):
            return f(*args, **kwargs)

        presented = csrf_proof_from_request()
        cookie = request.cookies.get(CSRF_COOKIE_NAME) or ""
        if not presented or not cookie or not hmac.compare_digest(presented, cookie):
            return (
                jsonify(
                    {
                        "error": "CSRF validation failed",
                        "code": 403,
                        "hint": f"Send the {csrf_header_name()} header or the {CSRF_FIELD_NAME} field with the value from the {CSRF_COOKIE_NAME} cookie.",
                    }
                ),
                403,
            )
        if not verify_csrf_token(presented):
            return jsonify({"error": "CSRF token is expired or invalid", "code": 403}), 403
        return f(*args, **kwargs)

    return decorated


#: Name of the double-submit cookie.  Readable by JavaScript by necessity --
#: the point of a double submit is that the client echoes the value back -- so
#: it carries no authority on its own and is worthless without the signature.
CSRF_COOKIE_NAME = "iqoqo_csrf"

#: CSRF tokens are short-lived by design; the session they protect is not.
CSRF_TOKEN_TTL_SECONDS = 8 * 60 * 60


def csrf_header_name() -> str:
    """Return the request header carrying CSRF proof.

    Reads from configuration so a deployment behind a proxy that strips a
    particular header can rename it without a code change.

    Returns:
        The header name, lower-case.
    """
    return str(current_app.config.get("CSRF_HEADER_NAME", "X-CSRF-Token"))


def _csrf_key() -> bytes:
    """Return the key that signs CSRF tokens.

    Derived from the application secret rather than used directly, so the CSRF
    key is not the same byte string as the session cookie's signing key.  A
    deployment that rotated one would otherwise have to rotate both.

    Raises:
        RuntimeError: If no secret is available.  An unsigned CSRF token is not
            a CSRF token, so this fails rather than degrading.
    """
    secret = current_app.config.get("SECRET_KEY") or current_app.config.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("No SECRET_KEY available to sign CSRF tokens")
    return hmac.new(str(secret).encode("utf-8"), b"iqoqo-csrf", hashlib.sha256).digest()


def issue_csrf_token() -> str:
    """Mint a signed CSRF token.

    Returns:
        ``<random>.<expiry>.<signature>``.  The signature covers the random
        material and the expiry together, so neither can be edited.
    """
    issued_at = int(time.time())
    nonce = uuid.uuid4().hex
    payload = f"{nonce}.{issued_at}"
    signature = hmac.new(_csrf_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_csrf_token(token: str) -> bool:
    """Whether *token* is a well-formed, correctly signed, unexpired CSRF token.

    Args:
        token: The candidate, from the header or the cookie.

    Returns:
        True only when the signature verifies and the token is current.  Any
        malformed input returns False rather than raising, since this runs on
        the request path with attacker-controlled data.
    """
    try:
        nonce, issued_raw, signature = token.rsplit(".", 2)
        issued_at = int(issued_raw)
    except (ValueError, AttributeError):
        return False
    if not nonce or not signature:
        return False
    expected = hmac.new(_csrf_key(), f"{nonce}.{issued_at}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    age = int(time.time()) - issued_at
    return -_CSRF_CLOCK_SKEW_SECONDS <= age <= CSRF_TOKEN_TTL_SECONDS


#: Tolerance for a token minted slightly in the future, which happens when the
#: browser and the API container disagree by a second or two.
_CSRF_CLOCK_SKEW_SECONDS = 60


def set_csrf_cookie(response):
    """Attach a fresh CSRF cookie to *response*.

    Called on the confirmation pages, which is where a token is first needed.
    Minting it there rather than on every response keeps it off the hot path and
    keeps the cookie's lifetime tied to the page that uses it.

    Args:
        response: The response to mutate.

    Returns:
        The same response, for chaining.
    """
    token = issue_csrf_token()
    # Not `secure=` unconditionally: a local development instance on plain HTTP
    # would then never receive the cookie and CSRF protection would look broken
    # rather than absent.  Sent over HTTPS in any deployment that sets a public
    # origin, which the production configuration requires.
    is_https = request.is_secure or bool(str(current_app.config.get("PUBLIC_APP_URL", "")).startswith("https://"))
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,
        secure=is_https,
        # `strict`, not `lax`: the cookie must survive no cross-site navigation
        # whatsoever, and nothing legitimate reads it off a cross-site arrival.
        samesite="Strict",
        path="/",
        max_age=CSRF_TOKEN_TTL_SECONDS,
    )
    return response


#: Name of the double-submit form field, used by the server-rendered
#: confirmation pages.  An HTML form cannot set a request header, so the SPA
#: variant uses the header above and this variant uses the field.  Both are
#: compared against the same signed cookie.
CSRF_FIELD_NAME = "csrf_token"


def csrf_proof_from_request() -> str:
    """Return the CSRF proof presented by the current request.

    Reads the header first, then the form field, so a client that sends both is
    unambiguous -- and so an attacker cannot downgrade the check by supplying a
    junk header alongside a valid field.

    Only ``application/x-www-form-urlencoded`` and ``multipart/form-data``
    bodies are parsed for the field.  Triggering form parsing from any content
    type would let a request whose body is JSON or XML be read as a form, which
    changes how an unrelated payload is interpreted.

    Returns:
        The presented value, or an empty string.
    """
    header = request.headers.get(csrf_header_name()) or ""
    if header:
        return header
    if request.mimetype in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        try:
            return str(request.form.get(CSRF_FIELD_NAME) or "")
        except Exception:
            # A malformed body must fail the check, never raise past it.
            return ""
    return ""


def enforce_csrf_if_cookie_authenticated() -> tuple[str, int] | None:
    """Validate CSRF proof for a state-changing, cookie-authenticated request.

    Called by the confirmation POST endpoints, which need it as an explicit step
    rather than a decorator because they render a page on failure rather than a
    JSON error -- a JSON body at a form post target is a browser-visible failure
    the user cannot act on.

    Returns:
        An ``(message, status)`` pair when the proof is missing or invalid, or
        None when the request may proceed.
    """
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    if not getattr(g, "authenticated_via_cookie", False):
        return None

    presented = csrf_proof_from_request()
    cookie = request.cookies.get(CSRF_COOKIE_NAME) or ""
    expired = "This form has expired. Reload the page and try again.", 403
    if not presented or not cookie or not hmac.compare_digest(presented, cookie):
        return expired
    if not verify_csrf_token(presented):
        return expired
    return None


def require_permission(perm_name: PermissionName):
    """Build a decorator that requires one named permission.

    Denies by default. The permission is resolved from the caller's role set at
    request time, so a role change takes effect on the next request without needing
    a session refresh."""

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
    """Short-hand for requiring the admin role rather than a single permission.

    Use when a route is administrative as a whole, rather than protected by one
    capability that could be delegated."""

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
