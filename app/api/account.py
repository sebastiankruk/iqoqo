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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Email verification and confirmed account deletion.

The route shape follows one rule: **a ``GET`` never changes anything.**

Mail clients fetch link targets.  Preview panes render them.  Corporate link
scanners fetch every URL in an inbound message the moment it arrives, and
security appliances rewrite and re-request them.  Browsers prefetch links that
appear to be navigations.  Any of those would delete an account if a ``GET``
could, so every ``GET`` here renders a page and every irreversible effect lives
behind a ``POST`` that additionally requires an authenticated session for the
account the token belongs to.

The final confirmation therefore requires **two** things: the token, which
proves the request was made from this mailbox, and a live session for the same
account, which proves the person confirming is the person who owns it.  Neither
is sufficient alone.  The email URL by itself is not a credential -- that is the
specific weakness this design exists to avoid, since a forwarded or archived
deletion mail would otherwise be enough to destroy an account.

Endpoint inventory:

``POST /api/account/email/verification-request``
    Authenticated, rate-limited. Sends a verification link to the current address.
``PUT  /api/account/email``
    Authenticated, rate-limited. Changes the address, clearing verification and
    invalidating every outstanding token.
``GET  /api/account/email/verify``
    Renders the confirmation page. No state change.
``POST /api/account/email/verify``
    Consumes the token and marks the address verified.
``POST /api/account/deletion/request``
    Authenticated, rate-limited. Creates the pending request and mails the link.
``GET  /api/account/deletion/confirm``
    Renders the confirmation page. No state change.
``POST /api/account/deletion/confirm``
    Consumes the token and deletes the account.
``GET  /api/account/deletion/status``
    Whether a request is pending, for the profile page.
``GET  /api/account/csrf``
    Mints a CSRF token for the JSON client.
"""

from __future__ import annotations

import logging
import uuid
from html import escape

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.core import account_lifecycle, account_tokens, mail_service
from app.core.account_tokens import AccountTokenPurpose, MailUnavailableError
from app.core.limiter import limiter
from app.db.models import User, db

from . import account_pages
from .decorators import (
    CSRF_COOKIE_NAME,
    CSRF_FIELD_NAME,
    enforce_csrf_if_cookie_authenticated,
    issue_csrf_token,
    require_auth,
    set_csrf_cookie,
)

logger = logging.getLogger(__name__)

account_bp = Blueprint("account", __name__, url_prefix="/api/account")

#: The two paths an emailed link can point at.  Kept as constants because the
#: rendered sign-in page echoes one back into the browser, and a caller-supplied
#: path there would be an open redirect.
_EMAIL_VERIFY_PATH = "/api/account/email/verify"
_DELETION_CONFIRM_PATH = "/api/account/deletion/confirm"

#: Longest accepted token in a query string.  A real one is 43 characters; this
#: only bounds the work an oversized parameter can cause before it reaches a
#: digest computation.
_MAX_TOKEN_LENGTH = 128


def _current_user() -> User | None:
    """Return the authenticated account, or None.

    ``require_auth`` has already established that the account exists and is
    active, so a None here means the session was resolved to a row that has since
    changed -- treated as absent rather than trusted.

    Returns:
        The account, or None.
    """
    return db.session.get(User, getattr(g, "user_id", None))


def _rate_limit_key() -> str:
    """Rate-limit bucket key for an authenticated account-lifecycle endpoint.

    Keyed on the account, not the source address.  These endpoints send mail, and
    what mail throttling protects is the receiving mailbox's tolerance -- so the
    bucket that matters is the one per account.  An IP-keyed bucket would let a
    single host exhaust a victim's quota while leaving the victim's own retries
    unaffected, which protects the attacker from the victim.

    Returns:
        The account id, or ``"anon"`` when unauthenticated.  Never an IP: an
        endpoint behind this decorator is always authenticated, and falling back
        to a shared address bucket would put unrelated users in one budget.
    """
    return str(getattr(g, "user_id", None) or "anon")


def _token_from_request() -> str:
    """Extract the token from a query string or form body.

    Args:
        None.

    Returns:
        The raw token, or an empty string.
    """
    candidate = request.values.get("token") or ""
    if not isinstance(candidate, str):  # pragma: no cover - werkzeug always yields str here
        return ""
    return candidate[:_MAX_TOKEN_LENGTH]


def _csrf_field() -> str:
    """Render the hidden CSRF input for a confirmation form.

    Mirrors :func:`enforce_csrf_if_cookie_authenticated` exactly, by reading the
    same ``g.authenticated_via_cookie`` flag.  That symmetry is the point: a
    field emitted for a request whose CSRF will never be checked would be a
    hidden input carrying a credential that means nothing, and -- because the
    field's value changes per response -- it would make an otherwise identical
    page render differently on every GET, which is precisely the instability the
    scanner-safety requirement rules out.

    Returns:
        An HTML fragment, or an empty string when there is nothing to prove.
    """
    if not getattr(g, "authenticated_via_cookie", False):
        return ""
    token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    if not token:
        return ""
    return f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{escape(token, quote=True)}">'


def _csrf_failure_page(message: str) -> Response:
    """Render a CSRF rejection as a page the user can act on.

    Args:
        message: Human-readable explanation.

    Returns:
        A 403 HTML response, using the same hardened headers as every other page
        this flow renders.
    """
    return account_pages.expired_form_page(detail=message)


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


@account_bp.route("/email/verification-request", methods=["POST"])
@require_auth
@limiter.limit("3 per hour", key_func=_rate_limit_key)
def request_email_verification():
    """Send a verification link to the account's current address.

    Rate limited per account rather than per IP, because the thing being
    protected is the mailbox's tolerance for mail, and an IP bucket would let
    one attacker exhaust a victim's quota from a single host.

    The response never varies on whether the address is already verified, so
    this cannot be used to learn anything about an account the caller does not
    already own.
    """
    user = _current_user()
    if user is None:
        return jsonify({"error": "User not found"}), 404

    if user.is_email_verified:
        return jsonify({"success": True, "message": "If the address needs verification, a link is on its way."})

    try:
        account_lifecycle.send_verification(user)
    except MailUnavailableError:
        # Names the misconfiguration but reveals nothing about the account: the
        # caller is already authenticated as this user, so there is no
        # enumeration to protect here, and an operator needs the key name.
        logger.error("Email verification is unavailable: outbound mail is not configured or not delivering")
        return (
            jsonify(
                {
                    "error": "Verification email could not be sent. This instance is not configured to send mail; "
                    "ask your administrator to configure it.",
                    "code": 503,
                }
            ),
            503,
        )
    except mail_service.MailConfigurationError:
        logger.error("Email verification is unavailable: mail configuration is invalid")
        return (
            jsonify(
                {
                    "error": "Verification email could not be sent. This instance is not configured to send mail; "
                    "ask your administrator to configure it.",
                    "code": 503,
                }
            ),
            503,
        )

    return jsonify({"success": True, "message": "If the address needs verification, a link is on its way."})


@account_bp.route("/email", methods=["PUT"])
@require_auth
@limiter.limit("3 per hour", key_func=_rate_limit_key)
def change_account_email():
    """Change the account's email address.

    Changing the address drops verification and invalidates every outstanding
    token, because both were issued to a mailbox that no longer relates to this
    account.  A fresh verification link goes to the new address, so the new
    address has to prove itself before it can be used for anything -- including
    for deleting the account.

    Returns 409 when the address already belongs to another account.  That is
    not an enumeration risk: the caller is authenticated, and an address being
    taken is information they need in order to correct a typo.
    """
    user = _current_user()
    if user is None:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object body is required", "code": 400}), 400

    candidate = data.get("email")
    if not mail_service.is_valid_address(candidate):
        return jsonify({"error": "A valid email address is required", "code": 400}), 400

    normalized = str(candidate).strip().lower()
    if normalized == (user.email or "").strip().lower():
        return jsonify({"success": True, "data": user.to_private_dict()})

    taken = db.session.execute(db.select(User).where(User.email == normalized)).scalar_one_or_none()
    if taken is not None:
        return jsonify({"error": "That email address is already registered to another account", "code": 409}), 409

    account_lifecycle.set_email(user, normalized)
    db.session.commit()

    # Best-effort: the address has already changed, and refusing to say so
    # because a mail relay is down would leave the caller believing their change
    # failed.  They simply have an unverified address, which the response states.
    mailed = True
    try:
        account_lifecycle.send_verification(user)
    except (MailUnavailableError, mail_service.MailConfigurationError):
        mailed = False
        logger.warning("Address changed for user %s but the verification mail could not be sent", user.id)

    payload = user.to_private_dict()
    payload["verification_email_sent"] = mailed
    return jsonify({"success": True, "data": payload})


@account_bp.route("/email/verify", methods=["GET"])
def verify_email_page():
    """Render the email-verification confirmation page.

    Side-effect free by contract.  A scanner, a preview pane or a prefetcher
    that fetches this URL gets exactly the bytes a human would, and the token
    remains outstanding.

    An anonymous visitor holding a valid token is told to sign in rather than
    shown a form they cannot submit: verification also requires the account's
    session, because a verification token found in a forwarded mail should not
    be usable on its own.
    """
    token = _token_from_request()
    row = account_tokens.lookup_outstanding(token, AccountTokenPurpose.EMAIL_VERIFICATION)

    if row is None:
        return account_pages.invalid_link_page(action="verify")

    if getattr(g, "user_id", None) is None:
        return set_csrf_cookie(account_pages.sign_in_page(next_path=_EMAIL_VERIFY_PATH))

    if row.user_id != g.user_id:
        return account_pages.invalid_link_page(action="verify")

    user = _current_user()
    if user is None:  # pragma: no cover - require_auth-equivalent already guarantees this
        return account_pages.invalid_link_page(action="verify")

    response = account_pages.email_verification_page(account_hint=user.email, csrf_field=_csrf_field())
    return set_csrf_cookie(response)


@account_bp.route("/email/verify", methods=["POST"])
@require_auth
def confirm_email_verification():
    """Consume a verification token and mark the address verified.

    Requires an authenticated session for the same account.  A token is proof
    of mailbox control, not of identity, so on its own it must not be able to
    change an account's state.

    A failure is reported as a page rather than JSON because the caller is a
    form post, and a user staring at a JSON error has nothing to do about it.
    """
    csrf_error = enforce_csrf_if_cookie_authenticated()
    if csrf_error is not None:
        return _csrf_failure_page(csrf_error[0])

    user = _current_user()
    token = _token_from_request()

    try:
        consumed = account_tokens.consume_token(token, AccountTokenPurpose.EMAIL_VERIFICATION)
    except SQLAlchemyError:
        db.session.rollback()
        logger.error("Email verification failed while consuming a token", exc_info=True)
        return account_pages.invalid_link_page(action="verify"), 500

    if consumed is None or consumed.user_id != g.user_id:
        db.session.rollback()
        return account_pages.invalid_link_page(action="verify")

    # The address must still be the one the token was issued for.  A token row
    # survives an address change only if something bypassed
    # `account_lifecycle.set_email`, so this is the belt to that braces.
    if user is None or consumed.email != (user.email or "").strip().lower():
        db.session.rollback()
        return account_pages.invalid_link_page(action="verify")

    user.mark_email_verified("local")
    db.session.commit()
    logger.info("Verified the email address for user %s via a local confirmation link", user.id)

    return account_pages.success_page(
        heading="Email address confirmed",
        detail="You can close this page and return to your profile.",
    )


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------


@account_bp.route("/deletion/request", methods=["POST"])
@require_auth
@limiter.limit("3 per hour", key_func=_rate_limit_key)
def request_account_deletion():
    """Create a pending deletion request and mail the confirmation link.

    Deletes nothing.  The account, its library and its data are untouched until
    the link is opened and the confirmation submitted, so a user who changes
    their mind simply does nothing.

    Requires a verified address.  There is deliberately no weaker path for an
    account without one: an unverified address may belong to someone else, so
    mailing a deletion link to it would hand that someone an account-deletion
    credential.  The response tells the user exactly what to do instead.
    """
    user = _current_user()
    if user is None:
        return jsonify({"error": "User not found"}), 404

    try:
        account_lifecycle.request_deletion(user)
    except account_lifecycle.NeedsVerifiedEmail:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Verify your email address before deleting your account.",
                    "code": 409,
                    "email_verified": False,
                }
            ),
            409,
        )
    except (MailUnavailableError, mail_service.MailConfigurationError):
        logger.error("Account deletion request could not be delivered: outbound mail is not available")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "The confirmation email could not be sent, so nothing has been changed. "
                    "This instance is not configured to send mail; ask your administrator to configure it.",
                    "code": 503,
                }
            ),
            503,
        )

    # 202: the request is recorded and the mail is on its way, but the account
    # is untouched. Returning 200 would imply the deletion itself is done.
    return jsonify({"success": True, "message": "Check your verified email address for a confirmation link."}), 202


@account_bp.route("/deletion/status", methods=["GET"])
@require_auth
def deletion_status():
    """Report whether a deletion request is awaiting confirmation."""
    user = _current_user()
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True, "data": account_lifecycle.pending_deletion_state(user)})


@account_bp.route("/deletion/confirm", methods=["GET"])
def deletion_confirm_page():
    """Render the account-deletion confirmation page.

    Side-effect free by contract, and this is the endpoint the specification
    cares about most: a mail scanner fetches this URL within seconds of the
    message arriving, before the user has read a word of it.  Nothing is
    consumed, nothing is deleted, and the rendered page is identical whether a
    human or a scanner asked for it.
    """
    token = _token_from_request()
    row = account_tokens.lookup_outstanding(token, AccountTokenPurpose.ACCOUNT_DELETION)

    if row is None:
        # One page for unknown, expired, superseded and already-consumed alike.
        return account_pages.invalid_link_page(action="delete")

    if getattr(g, "user_id", None) is None:
        return set_csrf_cookie(account_pages.sign_in_page(next_path=_DELETION_CONFIRM_PATH))

    if row.user_id != g.user_id:
        # Bound to one account. Rendering the form here would invite a user to
        # confirm something that would then be refused -- a confusing failure
        # that also confirms the token is live to whoever is signed in.
        return set_csrf_cookie(account_pages.invalid_link_page(action="delete"))

    user = _current_user()
    if user is None:  # pragma: no cover - lookup_outstanding already proved the row is live
        return account_pages.invalid_link_page(action="delete")

    response = account_pages.deletion_confirmation_page(account_hint=user.email, csrf_field=_csrf_field())
    return set_csrf_cookie(response)


@account_bp.route("/deletion/confirm", methods=["POST"])
@require_auth
def confirm_account_deletion():
    """Consume the token and permanently delete the account.

    Requires, in this order: a live session for the account the token belongs
    to, valid CSRF proof when that session came from a cookie, an unexpired
    single-use token, and a second confirmation of the permanent effect.  All
    four must hold, and the token consumption and the delete commit together.

    On success the response is a page: the account is gone, so the JSON client
    has nothing left to talk to, and the browser should not be left holding a
    session cookie for a user that no longer exists.
    """
    csrf_error = enforce_csrf_if_cookie_authenticated()
    if csrf_error is not None:
        return _csrf_failure_page(csrf_error[0])

    if request.form.get("confirm") != "delete":
        # The typed confirmation. Not a CSRF defence -- CSRF is already handled
        # above -- but it is the last checkpoint before something irreversible,
        # and it costs one field.
        return account_pages.deletion_confirmation_page(
            account_hint="your account",
            csrf_field=_csrf_field(),
        )

    token = _token_from_request()
    acting_user_id = getattr(g, "user_id", None)
    if not isinstance(acting_user_id, uuid.UUID):
        return jsonify({"error": "User not found"}), 404

    try:
        outcome = account_lifecycle.confirm_deletion(token, acting_user_id)
    except account_lifecycle.DeletionRejected:
        db.session.rollback()
        return account_pages.invalid_link_page(action="delete")
    except account_lifecycle.DeletionFailed:
        db.session.rollback()
        logger.error("Account deletion failed; the account and its pending request are unchanged")
        return account_pages.success_page(
            heading="Deletion could not be completed",
            detail="Nothing has been changed and your account is intact. Please try again.",
        )

    _notify_deletion_completed(outcome)

    response = account_pages.success_page(
        heading="Your account has been deleted",
        detail="Everything associated with it has been removed, and you are signed out everywhere. "
        "This cannot be undone.",
    )
    # The session cookie is the only thing left pointing at an account that no
    # longer exists. Clearing it means a stale browser cannot keep presenting it.
    response.delete_cookie("iqoqo_session", path="/")
    return response


def _notify_deletion_completed(outcome: account_lifecycle.DeletionOutcome) -> None:
    """Send the post-deletion notice, without ever blocking or undoing the delete.

    The account is already gone when this runs, and nothing here may change
    that.  Delivery is therefore attempted through the Celery queue first, and
    the direct send is the fallback when the queue is unreachable -- a mail
    relay being down must not turn a completed deletion into a failed request
    that the user retries against an account that no longer exists.

    Args:
        outcome: What was deleted, captured before the rows went.
    """
    rendered = account_lifecycle.account_mail.deletion_completed(outcome.display_name)
    try:
        from app.core.tasks import send_account_email_task

        send_account_email_task.delay(outcome.recipient, rendered.subject, rendered.text)
        return
    except Exception:
        logger.warning("Could not queue the deletion completion notice; sending it inline", exc_info=True)

    try:
        mail_service.get_mail_service().send(
            recipient=outcome.recipient,
            subject=rendered.subject,
            body_text=rendered.text,
        )
    except mail_service.MailError:
        # Deliberately swallowed. The deletion is committed and correct; a
        # missing courtesy notice is strictly better than an account that was
        # restored, or a 500 that invites the user to retry.
        logger.error("Could not deliver the deletion completion notice to a deleted account")


# ---------------------------------------------------------------------------
# CSRF for the JSON client
# ---------------------------------------------------------------------------


@account_bp.route("/csrf", methods=["GET"])
def csrf_token():
    """Mint a CSRF token for the JSON client.

    The confirmation pages set the same cookie themselves, so this exists only
    for the profile page's direct calls -- changing an address or requesting a
    deletion -- which go through axios rather than a form.
    """
    response = jsonify({"success": True, "data": {"csrf_token": issue_csrf_token(), "header_name": "X-CSRF-Token"}})
    return set_csrf_cookie(response)
