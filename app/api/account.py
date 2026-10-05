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

from flask import Blueprint, g, jsonify, request
from kombu.exceptions import KombuError
from sqlalchemy.exc import SQLAlchemyError

from app.core import account_lifecycle, account_tokens, mail_service
from app.core.account_tokens import AccountTokenPurpose, MailUnavailableError
from app.core.limiter import limiter
from app.db.models import User, db

from .decorators import (
    enforce_csrf_if_cookie_authenticated,
    issue_csrf_token,
    require_auth,
    set_csrf_cookie,
)

logger = logging.getLogger(__name__)

account_bp = Blueprint("account", __name__, url_prefix="/api/account")

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


def _link_unusable():
    """The one answer for every unusable-token case.

    Unknown, expired, consumed, superseded and wrong-account all look identical
    from outside. Distinguishing them would tell whoever holds an unreadable token
    how far they got, and would tell a legitimate user nothing, because in every
    case the next step is the same: ask for a new link.

    Returns:
        A ``(Response, 400)`` tuple.
    """
    return jsonify({"success": False, "usable": False, "error": "This link is no longer valid."}), 400


def _csrf_failure(message: str):
    """Build the 403 body for a rejected CSRF proof.

    Args:
        message: Human-readable explanation.

    Returns:
        A ``(Response, 403)`` tuple.
    """
    return jsonify({"success": False, "error": message, "code": 403}), 403


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
    except MailUnavailableError as exc:
        # The two failures are told apart on purpose. "Not configured" and
        # "the relay refused the message" have different causes and different
        # fixes -- one is an operator who never set MAIL_HOST, the other is a
        # host that was reachable and said no. Reporting both as "not
        # configured" sent a report of a live-but-refusing relay to the wrong
        # investigation entirely.
        logger.error("Email verification was not delivered (%s)", exc, exc_info=True)
        return _mail_failure_response(delivery_problem=True)
    except mail_service.MailConfigurationError as exc:
        logger.error("Email verification is unavailable: mail configuration is invalid (%s)", exc)
        return _mail_failure_response(delivery_problem=False)

    return jsonify({"success": True, "message": "If the address needs verification, a link is on its way."})


def _mail_failure_response(*, delivery_problem: bool):
    """Build the 503 body for a send that did not happen.

    Args:
        delivery_problem: True when the relay was reachable and refused or
            dropped the message, False when mail is not usable as configured.

    Returns:
        A ``(Response, 503)`` tuple. 503 throughout: nothing was sent and no
        state changed, so the caller may retry once the cause is fixed.
    """
    detail = (
        "The mail server could not be reached or refused the message. Nothing has been changed; "
        "please try again shortly, and tell your administrator if it keeps happening."
        if delivery_problem
        else "This instance is not configured to send mail. Ask your administrator to configure it. " "Nothing has been changed."
    )
    return jsonify({"error": detail, "code": 503}), 503


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
@require_auth
def email_verification_state():
    """Report whether a verification token can be spent, without spending it.

    The confirmation screen is a frontend route; this is the JSON it reads to
    decide what to render. Side-effect free by contract, because the URL it is
    called with is the one that arrives by email, and mail clients, link
    previewers and security scanners fetch every link in a message within
    seconds of it landing -- long before a human opens it. A scanner must get the
    same answer as the user and change nothing.

    Requires the session for the account the token belongs to. A verification
    token proves mailbox control, not identity, so on its own it must not be able
    to change or even inspect an account's state.
    """
    user = _current_user()
    token = _token_from_request()

    if user is None:
        return jsonify({"success": False, "error": "User not found"}), 404

    row = account_tokens.lookup_outstanding(token, AccountTokenPurpose.EMAIL_VERIFICATION)
    if row is None or row.user_id != g.user_id:
        # One answer for unknown, expired, consumed, superseded and wrong-account
        # alike: distinguishing them would report how far a holder of an
        # unreadable token got.
        return jsonify({"success": True, "data": {"usable": False}})

    if user.is_email_verified:
        return jsonify({"success": True, "data": {"usable": False, "already_verified": True, "email": user.email}})

    return jsonify({"success": True, "data": {"usable": True, "email": user.email}})


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
        return _csrf_failure(csrf_error[0])

    user = _current_user()
    token = _token_from_request()

    try:
        consumed = account_tokens.consume_token(token, AccountTokenPurpose.EMAIL_VERIFICATION)
    except SQLAlchemyError:
        db.session.rollback()
        logger.error("Email verification failed while consuming a token", exc_info=True)
        return _link_unusable(), 500

    if consumed is None or consumed.user_id != g.user_id or user is None:
        db.session.rollback()
        return _link_unusable()

    # The address must still be the one the token was issued for. A token row
    # survives an address change only if something bypassed
    # `account_lifecycle.set_email`, so this is the belt to that braces.
    if consumed.email != (user.email or "").strip().lower():
        db.session.rollback()
        return _link_unusable()

    user.mark_email_verified("local")
    db.session.commit()
    logger.info("Verified the email address for user %s via a local confirmation link", user.id)

    return jsonify({"success": True, "data": {"email": user.email, "verified": True}})


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
    except MailUnavailableError as exc:
        logger.error("Account deletion request mail was not delivered (%s)", exc, exc_info=True)
        return _mail_failure_response(delivery_problem=True)
    except mail_service.MailConfigurationError as exc:
        logger.error("Account deletion request mail is unavailable: configuration is invalid (%s)", exc)
        return _mail_failure_response(delivery_problem=False)

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
@require_auth
def deletion_confirmation_state():
    """Report whether a deletion token can be spent, without spending it.

    The confirmation screen is a frontend route; this is the JSON it reads. This
    is the endpoint the specification cares about most, because the URL is the one
    that arrives by email and a security appliance will fetch it within seconds of
    the message landing -- before the recipient has read a word. Nothing is
    consumed, nothing is deleted, and a scanner gets exactly what the user gets.

    Requires the session for the account the token belongs to. Accepting a token
    from any authenticated session would make it a universal deletion key, which
    is precisely what binding it to one account prevents.
    """
    user = _current_user()
    token = _token_from_request()

    if user is None:
        return jsonify({"success": False, "error": "User not found"}), 404

    row = account_tokens.lookup_outstanding(token, AccountTokenPurpose.ACCOUNT_DELETION)
    if row is None or row.user_id != g.user_id:
        # One answer for unknown, expired, superseded, consumed and wrong-account
        # alike. A distinct reply would confirm to whoever is signed in that the
        # token is live.
        return jsonify({"success": True, "data": {"usable": False}})

    return jsonify({"success": True, "data": {"usable": True, "email": user.email}})


@account_bp.route("/deletion/confirm", methods=["POST"])
@require_auth
def confirm_account_deletion():
    """Consume the token and permanently delete the account.

    Requires, in order: a live session for the account the token belongs to, valid
    CSRF proof when that session came from a cookie, and an unexpired single-use
    token. The token consumption and the delete commit together.

    There is no separate "type DELETE to confirm" gate. There was one, requiring a
    `confirm=delete` field the rendered form never contained, so submitting the
    page re-displayed it and deleted nothing -- indistinguishable from a dead
    button. A fixed hidden field would not have fixed that; it would only have made
    the flow pass while proving nothing about intent, since a browser posts it
    automatically. What gates this is already explicit: a POST rather than a GET,
    a live session bound to this account, CSRF proof, and a single-use token.

    The confirmation screen itself is a frontend route; this endpoint is the
    mutation behind its button.
    """
    csrf_error = enforce_csrf_if_cookie_authenticated()
    if csrf_error is not None:
        return _csrf_failure(csrf_error[0])

    token = _token_from_request()
    acting_user_id = getattr(g, "user_id", None)
    if not isinstance(acting_user_id, uuid.UUID):
        return jsonify({"error": "User not found"}), 404

    try:
        outcome = account_lifecycle.confirm_deletion(token, acting_user_id)
    except account_lifecycle.DeletionRejected:
        db.session.rollback()
        return _link_unusable()
    except account_lifecycle.DeletionFailed:
        db.session.rollback()
        logger.error("Account deletion failed; the account and its pending request are unchanged")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "The account could not be deleted. Nothing has changed and your account is intact.",
                    "code": 500,
                }
            ),
            500,
        )

    _notify_deletion_completed(outcome)

    response = jsonify({"success": True, "data": {"deleted": True}})
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
    except (KombuError, OSError):
        # The queue is unavailable. `submit_task` in app.core.tasks catches the
        # same pair, so this mirrors the established convention for "the broker
        # is not reachable" rather than inventing a new one. Deliberately not a
        # bare `except Exception`: a bug inside the task wrapper should surface
        # as a 500 to be investigated, not be silently converted into an inline
        # send that hides it.
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

    Used by the profile page's direct calls -- changing an address, requesting a
    deletion -- and by the frontend confirmation routes before they read any
    token state.

    The token is minted once and used for both the body and the cookie. Minting
    separately gave two different tokens, so the value in the response body was
    never the one a client would echo back: `document.cookie` yields the cookie's,
    not the body's. It happened to work because both are validly signed, but the
    API was reporting a token no request could ever use.
    """
    minted = issue_csrf_token()
    response = jsonify({"success": True, "data": {"csrf_token": minted, "header_name": "X-CSRF-Token"}})
    return set_csrf_cookie(response, minted)
