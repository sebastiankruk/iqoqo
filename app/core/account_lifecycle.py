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
"""Account verification and irreversible-deletion orchestration.

Sits between the HTTP layer and :mod:`app.core.account_tokens`, and owns the two
things that must not be got subtly wrong: what mail goes out, and what happens
to the rows when an account is deleted.

Deletion plan
-------------

Deleting a user row has to take roughly twenty child tables with it, and both
obvious approaches fail:

* ``db.session.delete(user)`` on its own makes the ORM de-associate every loaded
  child.  Most references are nullable and survive that, but four are
  ``NOT NULL`` with no ``delete-orphan`` cascade, and the ORM would try to set
  them to ``NULL`` and fail the transaction.
* Relying entirely on the database's ``ON DELETE CASCADE`` is right on
  PostgreSQL, which is what production runs -- but SQLite does **not** enforce
  foreign keys unless ``PRAGMA foreign_keys=ON`` is set per connection, which
  this project does not do.  A cascade-only implementation would therefore
  behave differently in tests than in production, which is the worst of both.

So the plan is explicit: :data:`NOT_NULL_USER_REFERENCES` is emptied first, by
bulk statement, in full.  Everything else the ORM already cascades or
de-associates correctly and is left alone.

That list is the kind of thing that rots, so it is **verified against the model
metadata by a test**: a new ``NOT NULL`` foreign key to ``users`` fails
``tests/test_account_deletion.py::test_every_not_null_user_reference_is_covered_by_the_deletion_plan``
instead of surfacing as a deletion failure a user discovered.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from app.core import account_mail, account_tokens, mail_service
from app.core.account_tokens import AccountTokenPurpose, MailUnavailableError
from app.db.auth import AccountActionToken
from app.db.core import ItemStatusLog
from app.db.lending import LoanRequest
from app.db.models import OAuthExchangeCode, User, db
from app.db.roadmap import ReadingRoadmap

logger = logging.getLogger(__name__)

#: Child tables with a ``NOT NULL`` foreign key to ``auth.users`` that no ORM
#: relationship cascades, as ``(model, column)``.  These must be emptied before
#: the user row goes, or the delete fails on the constraint.
#:
#: Verified against ``db.metadata`` *and* against the live ``User`` mapper by
#: ``tests/test_account_deletion.py::TestDeletionPlanCoverage``, in both
#: directions: a new reference that is missing from here fails the suite, and so
#: does an entry here that is no longer needed.  The failure being prevented is a
#: hard error in the middle of an irreversible operation.
#:
#: ``AccountActionToken`` is in the list on purpose. Its foreign key does
#: ``ON DELETE CASCADE``, so PostgreSQL would clear it anyway -- but SQLite does
#: not enforce cascades, so relying on that would leave the test database and
#: production behaving differently.
NOT_NULL_USER_REFERENCES: tuple[tuple[type, str], ...] = (
    (AccountActionToken, "user_id"),
    (ItemStatusLog, "user_id"),
    (LoanRequest, "requester_id"),
    (ReadingRoadmap, "user_id"),
    (OAuthExchangeCode, "user_id"),
)


class AccountLifecycleError(Exception):
    """Base class for account lifecycle failures."""


class NeedsVerifiedEmail(AccountLifecycleError):
    """Deletion was requested for an account with no verified address.

    Carries the address that is present but unproven, so the caller can tell the
    user precisely what to do rather than just refusing.

    Args:
        current_email: The unverified address on the account, or None.
    """

    def __init__(self, current_email: str | None = None) -> None:
        super().__init__("Account deletion requires a verified email address")
        self.current_email = current_email


class DeletionRejected(AccountLifecycleError):
    """The deletion confirmation was refused.  Nothing has changed."""


class DeletionFailed(AccountLifecycleError):
    """The account-deletion transaction could not be completed.

    Raised with the session already rolled back, so the caller may retry or
    report a failure without leaving a half-deleted account behind.
    """


@dataclass(frozen=True)
class DeletionOutcome:
    """What a completed deletion did, for the audit log and the notice.

    Attributes:
        user_id: The account that was deleted.
        display_name: Its display name, captured before the row went.
        recipient: The verified address the completion notice goes to, captured
            before the row went.
        child_rows_removed: How many child rows the plan deleted explicitly,
            not counting the ORM's own cascades.
    """

    user_id: uuid.UUID
    display_name: str | None
    recipient: str
    child_rows_removed: int


def _now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def set_email(user: User, new_email: str) -> bool:
    """Change an account's address and revoke everything the old one authorised.

    Changing the address is a security event, not a profile edit: the new
    address is unproven, and any outstanding token was issued to a mailbox that
    no longer has anything to do with this account.  So the verification state is
    cleared and *both* token purposes are invalidated, before the caller sends
    anything to the new address.

    Args:
        user: The account being changed.
        new_email: The already-validated replacement address.

    Returns:
        True when the address actually changed.
    """
    previous = (user.email or "").strip().lower()
    candidate = new_email.strip().lower()
    if previous == candidate:
        return False
    user.email = candidate
    user.clear_email_verification()
    account_tokens.invalidate_tokens(user.id, None, commit=False)
    return True


def send_verification(user: User) -> None:
    """Mint a verification token and mail the link to the account's address.

    The token row is committed before the send is attempted, then retracted if
    delivery fails.  Retracting matters: a token the user never received would
    otherwise supersede the working one, leaving them unable to verify until it
    expired, with no error to explain why.

    Args:
        user: The account whose address should be verified.

    Raises:
        MailUnavailableError: If the message could not be delivered.  No
            outstanding token remains in that case.
        MailConfigurationError: Propagated from the mail boundary, wrapped.
    """
    _purge_expired()
    token, _row = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION, commit=True)
    try:
        link = mail_service.build_link("/api/account/email/verify", token)
        rendered = account_mail.email_verification(user.display_name, link)
        mail_service.get_mail_service().send(
            recipient=user.email,
            subject=rendered.subject,
            body_text=rendered.text,
        )
    except mail_service.MailConfigurationError:
        # Retract the token, then let the configuration error through unchanged.
        # It is a *different* kind of failure from a refused send -- mail is not
        # usable at all -- and the caller reports the two differently. Wrapping
        # it here collapsed that distinction before anyone could act on it.
        account_tokens.invalidate_tokens(user.id, AccountTokenPurpose.EMAIL_VERIFICATION, commit=True)
        raise
    except mail_service.MailDeliveryError as exc:
        account_tokens.invalidate_tokens(user.id, AccountTokenPurpose.EMAIL_VERIFICATION, commit=True)
        # `exc` is logged, not just its type: `MailDeliveryError` carries the
        # underlying SMTP exception class, and logging only `type(exc).__name__`
        # discarded the only signal that distinguishes "the relay refused this"
        # from "the relay was unreachable". No message body or token is logged.
        logger.warning("Verification mail for user %s was not delivered: %s", user.id, exc)
        raise MailUnavailableError(str(exc)) from exc
    logger.info("Issued an email-verification token for user %s", user.id)


def request_deletion(user: User) -> AccountActionToken:
    """Create a pending deletion request and mail the confirmation link.

    Deletes nothing.  The account and its data are untouched until
    :func:`confirm_deletion` runs, which is the entire reason this is separate
    from the irreversible step.

    Args:
        user: The authenticated account owner.

    Returns:
        The pending token row.

    Raises:
        NeedsVerifiedEmail: When the account has no verified address.
        MailUnavailableError: If the message could not be delivered, in which
            case no pending request is left behind.
    """
    if not user.has_verified_email:
        raise NeedsVerifiedEmail(user.email)

    _purge_expired()
    token, row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION, commit=True)
    try:
        link = mail_service.build_link("/api/account/deletion/confirm", token)
        rendered = account_mail.deletion_requested(
            user.display_name,
            link,
            expires_in_minutes=int(account_tokens.DELETION_TOKEN_TTL.total_seconds() // 60),
        )
        mail_service.get_mail_service().send(
            recipient=user.email,
            subject=rendered.subject,
            body_text=rendered.text,
        )
    except mail_service.MailConfigurationError:
        # See the note in `send_verification`: a configuration problem is a
        # different failure from a refused send and must not be flattened into it.
        account_tokens.invalidate_tokens(user.id, AccountTokenPurpose.ACCOUNT_DELETION, commit=True)
        raise
    except mail_service.MailDeliveryError as exc:
        account_tokens.invalidate_tokens(user.id, AccountTokenPurpose.ACCOUNT_DELETION, commit=True)
        logger.warning("Deletion-request mail for user %s was not delivered: %s", user.id, exc)
        raise MailUnavailableError(str(exc)) from exc

    logger.info("Created a pending deletion request for user %s", user.id)
    return row


def confirm_deletion(token: str, acting_user_id: uuid.UUID) -> DeletionOutcome:
    """Consume *token* and delete the account, atomically.

    Both effects are one transaction.  A caller whose token is rejected commits
    nothing; a caller whose delete fails rolls the consumption back with it, so a
    retry remains possible and a transient fault does not burn the token.

    Args:
        token: The raw token presented by the user.
        acting_user_id: The authenticated account making the request.  Must be
            the account the token was issued to; checked here as well as at the
            HTTP layer so the binding cannot be forgotten by a future caller.

    Returns:
        A record of what was removed, for the audit log and the notice.

    Raises:
        DeletionRejected: If the token was not usable, or belongs to another
            account.  Nothing has changed.
        DeletionFailed: If the database refused the delete.  Nothing has changed
            and the token remains outstanding.
    """
    consumed = account_tokens.consume_token(token, AccountTokenPurpose.ACCOUNT_DELETION)

    if consumed is None:
        # Roll back incidental work this request did earlier in the transaction;
        # a rejected confirmation must leave the session clean for whatever the
        # response path does next.
        db.session.rollback()
        raise DeletionRejected()

    if consumed.user_id != acting_user_id:
        db.session.rollback()
        logger.warning("Rejected a deletion confirmation presented by the wrong account")
        raise DeletionRejected()

    user = db.session.get(User, consumed.user_id)
    if user is None or not user.is_active:
        db.session.rollback()
        raise DeletionRejected()

    # The address the token was issued for is what the completion notice goes
    # to.  Read from the token row rather than the session, so a token that
    # outlived an address change cannot be used to notify a third party.
    recipient = consumed.email or user.email
    display_name = user.display_name
    user_id = user.id

    try:
        removed = _delete_account_rows(user)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Account deletion failed for user %s: %s", user_id, type(exc).__name__, exc_info=True)
        raise DeletionFailed("The account could not be deleted; nothing was changed") from exc

    # Detach anything the session still holds, so a later read within the same
    # request cannot resurrect a deleted row from the identity map.
    db.session.expunge_all()
    logger.info("Deleted account %s plus %d explicitly-referenced child row(s)", user_id, removed)
    return DeletionOutcome(user_id=user_id, display_name=display_name, recipient=recipient, child_rows_removed=removed)


def _delete_account_rows(user: User) -> int:
    """Remove every row belonging to *user*, returning the explicit child count.

    Runs inside the caller's transaction.  Ordering matters only in that the
    ``NOT NULL`` references must be gone before the user row; the ORM's cascades
    and de-associations happen at flush time, after this returns.

    Args:
        user: The account being deleted.

    Returns:
        The number of rows removed by explicit bulk statements.
    """
    removed = 0
    for model, column in NOT_NULL_USER_REFERENCES:
        result = db.session.execute(delete(model).where(getattr(model, column) == user.id))
        removed += int(getattr(result, "rowcount", 0) or 0)

    db.session.delete(user)
    db.session.flush()
    return removed


def pending_deletion_state(user: User) -> dict:
    """Describe whether *user* has a live deletion request awaiting confirmation.

    Args:
        user: The account to inspect.

    Returns:
        A dict with ``pending`` (bool) and ``expires_at`` (ISO 8601 or None).
    """
    row = db.session.execute(
        select(AccountActionToken).where(
            AccountActionToken.user_id == user.id,
            AccountActionToken.purpose == AccountTokenPurpose.ACCOUNT_DELETION.value,
            AccountActionToken.consumed_at.is_(None),
            AccountActionToken.expires_at > _now(),
        )
    ).scalar_one_or_none()
    return {
        "pending": row is not None,
        "expires_at": row.expires_at.isoformat() if row and row.expires_at else None,
    }


def purge_expired_tokens() -> int:
    """Delete expired token rows.

    Exposed for the scheduler and for operational use.  Issuance also purges, so
    a single-user instance never accumulates rows even with the scheduler off.

    Returns:
        The number of rows removed.
    """
    return _purge_expired()


def _purge_expired() -> int:
    """Delete expired token rows inside the current transaction.

    Called on every issuance.  Cheap -- it is an indexed range delete against a
    table whose rows all expire within a day -- and it means a deployment that
    never enables the scheduler still cannot accumulate dead tokens.

    Returns:
        The number of rows removed.
    """
    try:
        result = db.session.execute(delete(AccountActionToken).where(AccountActionToken.expires_at <= _now()))
        db.session.commit()
        return int(getattr(result, "rowcount", 0) or 0)
    except SQLAlchemyError:
        # A failed cleanup must never fail the operation that triggered it.
        db.session.rollback()
        logger.warning("Expired account-lifecycle token cleanup failed", exc_info=True)
        return 0
