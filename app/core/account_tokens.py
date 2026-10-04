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
"""Issuance and consumption of account-lifecycle tokens.

The two actions that must not be authorisable by a session alone -- proving
control of an email address, and confirming irreversible account deletion --
share one mechanism.  Four properties make it safe, and each is enforced
somewhere other than in this module's call sites, because "the code remembered
to check" is not a control:

**Only a keyed digest is stored.**  :func:`token_digest` derives an
HMAC-SHA256 over the token under a key mixed from ``SECRET_KEY`` and the token's
purpose.  A stolen database row, backup, or replica therefore contains no
usable credential, and -- because the purpose is in the key -- a digest minted
for one purpose is not even *recognisable* at the other purpose's endpoint.

**The token is 256 bits of ``secrets`` entropy** and carries no structure to
guess: no user id, no timestamp, no counter.  There is nothing in it for an
attacker to narrow a search with.

**Acceptance re-verifies under a row lock** (:func:`consume_token`).  A read
followed by a write is a race, and the race is the whole attack: two requests
carrying the same token would otherwise both see "outstanding" and both
succeed.  ``consume_token`` therefore takes the row ``FOR UPDATE`` inside the
caller's transaction, so the second request blocks and then observes
``consumed_at``.

**Supersession is a schema constraint.**  At most one outstanding token may
exist per ``(user_id, purpose)``; see the partial unique index on
:class:`~app.db.auth.AccountActionToken`.  Resending invalidates the previous
token even when two requests race.

Timing note: every failure path in this module returns the same
:class:`TokenRejection` shape and takes a comparable amount of work, so a caller
cannot distinguish "no such token" from "expired" from "wrong purpose" by
stopping time.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.auth import AccountActionToken, AccountTokenPurpose
from app.db.models import User, db

logger = logging.getLogger(__name__)

#: Raw token entropy in bytes.  ``secrets.token_urlsafe(32)`` yields 43
#: URL-safe base64 characters carrying 256 bits.  The specification's floor is
#: 32 bytes; exceeding it costs 12 characters in a link and buys nothing
#: measurable, so the floor is met exactly rather than padded.
TOKEN_ENTROPY_BYTES = 32

#: Deletion confirmation lifetime.  Fixed at 30 minutes by specification: long
#: enough for the user to find the mail, sign in on another device and click
#: through, short enough that a link forwarded to a shared mailbox has little
#: value by the time it is used.  The 7-day session lifetime is deliberately
#: *not* used as the token lifetime — the session proves who is asking, the
#: token proves the request is still wanted.
DELETION_TOKEN_TTL = timedelta(minutes=30)

#: Email verification lifetime.  Longer than the deletion token because it is
#: the recovery path for an account that cannot otherwise reach its own inbox
#: settings, and because it authorises nothing irreversible on its own.
VERIFICATION_TOKEN_TTL = timedelta(hours=24)


class TokenError(Exception):
    """Base class for token failures that callers may surface to a user."""


class MailUnavailableError(TokenError):
    """Outbound mail could not be sent, so the token was never delivered."""


@dataclass(frozen=True)
class TokenRejection:
    """Why a presented token was refused.

    A single value type for every rejection, so a caller's error branch cannot
    accidentally disclose more than another: the HTTP layer maps all of them to
    one response.

    Attributes:
        reason: A stable, non-secret machine-readable tag. Safe to log.
    """

    reason: str


#: The single rejection returned for every failure.  Distinct reasons are kept
#: for logging and for assertions in tests, never for the response body.
REJECTED = TokenRejection(reason="rejected")


def _secret_key() -> bytes:
    """Return the application secret as bytes.

    Raises:
        RuntimeError: If no secret is reachable.  Minting a token without a
            key would silently degrade the digest to an unkeyed hash, so this
            fails loudly rather than continuing.
    """
    from flask import current_app

    secret = current_app.config.get("SECRET_KEY") or current_app.config.get("JWT_SECRET_KEY")
    if not secret:
        # Same fallback order as `app.db.settings._get_fernet_cipher`, so the
        # two never disagree about which secret is in force.
        import os

        secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("No SECRET_KEY available to key account-lifecycle token digests")
    return str(secret).encode("utf-8")


def token_digest(token: str, purpose: AccountTokenPurpose | str) -> str:
    """Return the stored digest for *token* at *purpose*.

    The purpose is mixed into the key rather than appended to the message.  That
    makes a digest purpose-bound as well as the row it is stored in, so a token
    captured from one flow cannot be presented to the other and be recognised:
    the lookup misses as though the token had never existed, rather than hitting
    a row and failing a separate purpose comparison.

    Args:
        token: The raw token as presented by the user.
        purpose: The purpose the token was minted for.

    Returns:
        Lowercase hex HMAC-SHA256, 64 characters.
    """
    purpose_value = purpose.value if isinstance(purpose, AccountTokenPurpose) else str(purpose)
    derived = hmac.new(_secret_key(), purpose_value.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(derived, token.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_token() -> str:
    """Return a fresh URL-safe token carrying :data:`TOKEN_ENTROPY_BYTES` of entropy."""
    return secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)


def _ttl_for(purpose: AccountTokenPurpose) -> timedelta:
    """Return the lifetime of a token at *purpose*."""
    if purpose is AccountTokenPurpose.ACCOUNT_DELETION:
        return DELETION_TOKEN_TTL
    return VERIFICATION_TOKEN_TTL


def issue_token(
    user: User,
    purpose: AccountTokenPurpose,
    *,
    now: datetime | None = None,
    commit: bool = True,
) -> tuple[str, AccountActionToken]:
    """Mint a token for *user* and return ``(raw_token, row)``.

    Any previously outstanding token for the same ``(user, purpose)`` is retired
    first.  That is belt-and-braces on top of the partial unique index: the
    index is what makes supersession correct under concurrency, and this delete
    is what keeps the common path from having to catch an ``IntegrityError``.

    Args:
        user: The account the token authorises.
        purpose: What the token may be spent on.
        now: Override for the current time, for tests.
        commit: Whether to commit.  ``False`` lets a caller batch the write into
            a larger transaction.

    Returns:
        The raw token — which exists only in this return value and the email it
        goes into — and the persisted row.

    Raises:
        SQLAlchemyError: If the row could not be written.
    """
    issued_at = now or datetime.now(UTC)
    raw = generate_token()

    # Retire the previous token for this purpose.  Deliberately scoped to this
    # account and purpose: an invalidation must never disturb a verification
    # token because a deletion link was resent, or vice versa.
    #
    # The expunge afterwards is narrow -- token rows only.  The bulk DELETE is
    # invisible to the ORM's identity map, which still holds the retired row, and
    # SQLite reuses the freed primary key on the next INSERT, so the new row
    # would otherwise be flushed onto an identity the session believes it owns.
    # A blanket `expunge_all()` would also detach the `User` passed in here,
    # which every caller keeps using after issuance.
    db.session.execute(
        db.delete(AccountActionToken).where(
            AccountActionToken.user_id == user.id,
            AccountActionToken.purpose == purpose.value,
        )
    )
    _expunge_consumed_tokens()

    row = AccountActionToken(
        user_id=user.id,
        purpose=purpose.value,
        token_digest=token_digest(raw, purpose),
        email=user.email,
        created_at=issued_at,
        expires_at=issued_at + _ttl_for(purpose),
    )
    db.session.add(row)
    if commit:
        db.session.commit()
    return raw, row


def invalidate_tokens(
    user_id: uuid.UUID | str,
    purpose: AccountTokenPurpose | None = None,
    *,
    commit: bool = True,
) -> int:
    """Retire outstanding tokens for an account, optionally for one purpose only.

    Args:
        user_id: The account whose tokens are being retired.
        purpose: Restrict to a single purpose, or None for all of them.
        commit: Whether to commit.

    Returns:
        The number of rows retired.
    """
    conditions = [AccountActionToken.user_id == user_id, AccountActionToken.consumed_at.is_(None)]
    if purpose is not None:
        conditions.append(AccountActionToken.purpose == purpose.value)
    result = db.session.execute(db.delete(AccountActionToken).where(*conditions))
    if commit:
        db.session.commit()
    return int(getattr(result, "rowcount", 0) or 0)


def lookup_outstanding(token: str, purpose: AccountTokenPurpose) -> AccountActionToken | None:
    """Return the outstanding row matching *token*, or None.

    Read-only, for rendering the confirmation page.  It deliberately does **not**
    report *why* a token was rejected: the page says the same thing for an
    unknown, expired, consumed and superseded token alike.

    The bound row must still belong to a live account whose address has not
    moved since issue time.  Without that check the confirmation page would
    render for a token whose user was deleted or whose email was changed, which
    is both misleading and a small information leak.

    Args:
        token: The raw token from the request.
        purpose: The purpose this endpoint authorises.

    Returns:
        The matching row, or None.
    """
    if not token or len(token) > 128:
        # A URL-safe 43-character token is the only shape that can ever match.
        # Bounding the length before the query keeps an attacker from making
        # the digest computation arbitrarily expensive.
        return None
    try:
        digest = token_digest(token, purpose)
    except RuntimeError:
        logger.error("Cannot evaluate an account-lifecycle token: no SECRET_KEY in scope")
        return None

    row = db.session.execute(
        select(AccountActionToken).where(
            AccountActionToken.token_digest == digest,
            AccountActionToken.purpose == purpose.value,
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if _as_utc(row.expires_at) <= _now():
        return None
    user = db.session.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    return row


def consume_token(token: str, purpose: AccountTokenPurpose) -> AccountActionToken | None:
    """Atomically claim *token* and return the row it was.

    The claim is a conditional ``DELETE ... RETURNING`` scoped to outstanding
    rows whose expiry has not passed.  Two concurrent confirmations carrying the
    same token therefore produce exactly one winner: the database decides, not
    the order in which two requests happened to read the row.  A
    read-then-write would let both through.

    The caller is responsible for the surrounding transaction, so that claiming
    the token and applying its effect commit or roll back together.  This
    function never commits.

    Args:
        token: The raw token from the request.
        purpose: The purpose this endpoint authorises.

    Returns:
        The consumed row, or None if the token was unknown, expired, already
        spent, superseded, or issued for another purpose.
    """
    if not token or len(token) > 128:
        return None
    try:
        digest = token_digest(token, purpose)
    except RuntimeError:
        logger.error("Cannot evaluate an account-lifecycle token: no SECRET_KEY in scope")
        return None

    now = _now()
    # SQLite stores `DateTime` naive while `now` is aware. The SQL comparison is
    # fine -- it happens in the database -- but SQLAlchemy's default
    # `synchronize_session='evaluate'` re-checks the criteria *in Python*
    # against whatever the session already holds, and that comparison raises
    # TypeError on a mismatched offset. That turned every deletion confirmation
    # into a 500 on SQLite, which is every developer machine and the whole test
    # suite. Binding a naive value there keeps both dialects on one code path;
    # PostgreSQL compares aware to aware and is unaffected.
    if db.session.get_bind().dialect.name == "sqlite":
        now = now.replace(tzinfo=None)
    try:
        row = db.session.execute(
            db.delete(AccountActionToken)
            .where(
                AccountActionToken.token_digest == digest,
                AccountActionToken.purpose == purpose.value,
                AccountActionToken.consumed_at.is_(None),
                AccountActionToken.expires_at > now,
            )
            .returning(AccountActionToken.user_id, AccountActionToken.email)
            .execution_options(synchronize_session=False)
        ).first()
    except SQLAlchemyError:
        # Covers `IntegrityError` too, which subclasses it -- hence no separate
        # clause for that. A conditional DELETE cannot insert, so an integrity
        # failure here would mean the schema rejected something unexpected;
        # logging under the broader handler is honest about that.
        db.session.rollback()
        logger.error("Account-lifecycle token consumption failed", exc_info=True)
        return None

    if row is None:
        return None
    # `synchronize_session=False` means the session still holds a now-stale row
    # for the token just consumed.  Expunge *only the token rows* -- never
    # `expunge_all()`, which also detaches the `User` a caller has already
    # loaded and intends to mutate.  Email verification did exactly that:
    # `mark_email_verified` on a detached object, a commit that persisted
    # nothing, and a success page shown to a user whose address was still
    # unverified.
    _expunge_consumed_tokens()
    return AccountActionToken(user_id=row.user_id, purpose=purpose.value, email=row.email, consumed_at=now)


def _expunge_consumed_tokens() -> None:
    """Detach only :class:`AccountActionToken` instances from the session.

    Narrow on purpose. The conditional ``DELETE`` used for consumption bypasses
    the identity map, so any token row the session still references is stale and
    could be handed back to a caller or written over on a primary-key reuse.
    Everything else in the session is live and belongs to the caller.
    """
    for instance in list(db.session.identity_map.values()):
        if isinstance(instance, AccountActionToken):
            db.session.expunge(instance)


def mark_verified_from_oidc(user: User, claims: dict | None) -> bool:
    """Mark *user*'s address verified when a validated OIDC response says so.

    Trust is narrow on purpose.  The claim is only honoured when it is present
    and literally true; a missing claim, ``false``, or a non-boolean truthy
    value (``"false"`` as a string, ``1``) all leave the address unverified.

    That string case is not hypothetical.  Several OpenID providers serialise
    ``email_verified`` as the *string* ``"true"``, and a naive truthiness check
    would read ``"false"`` as verified -- the exact inverse of the claim.

    Args:
        user: The account signed in through the federated flow.
        claims: The validated identity claims.  Must have been verified by the
            OIDC library first; this function trusts the caller's validation
            and only interprets the claim.

    Returns:
        True when the address was newly marked verified.
    """
    if not isinstance(claims, dict):
        return False
    verified = claims.get("email_verified")
    if verified is not True and verified != "true":  # noqa: E712 - identity is the point
        return False
    if user.email_verified_at is not None:
        return False
    user.mark_email_verified("oidc")
    return True


def _now() -> datetime:
    """Return an aware UTC timestamp.

    Returns:
        The current time, always timezone-aware.
    """
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime:
    """Normalise a stored timestamp to aware UTC.

    SQLite round-trips ``DateTime(timezone=True)`` as a naive value, so a token
    read back from the test database would otherwise be compared against an
    aware ``now()`` and raise.  Production PostgreSQL is already aware, making
    this a no-op there.

    Args:
        value: The stored timestamp.

    Returns:
        An aware UTC datetime.

    Raises:
        ValueError: If *value* is None, which would be a corrupt row: every
            token carries a NOT NULL expiry, and treating it as "never expires"
            is the one failure mode that must not degrade silently.
    """
    if value is None:
        raise ValueError("account_action_tokens.expires_at is NULL; refusing to treat the token as live")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
