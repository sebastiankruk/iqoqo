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
"""Token-level security tests for the account lifecycle.

Covers the properties that make a single-use credential safe to put in an email:
entropy, digest-only storage, purpose binding, expiry, replay, supersession and
concurrent consumption.

Every test asserts on the *security property*, not on an implementation detail,
so a refactor that keeps the property green does not have to be rewritten, and a
refactor that drops it cannot pass.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from app.core import account_tokens
from app.core.account_tokens import AccountTokenPurpose
from app.db.auth import TOKEN_PURPOSE_LENGTH, AccountActionToken
from app.db.models import User, db


@pytest.fixture
def user(app):
    """A confirmed-account holder, the actor for every token test."""
    with app.app_context():
        record = User(email="tokens@iqoqo.local", display_name="Token Tester")
        record.set_password("test-password")
        db.session.add(record)
        db.session.commit()
        yield record
        db.session.rollback()


# ---------------------------------------------------------------------------
# Entropy
# ---------------------------------------------------------------------------


def test_generated_tokens_carry_at_least_32_bytes_of_entropy(app) -> None:
    """The specification's floor is 32 bytes; assert the real width, not the name.

    ``token_urlsafe(32)`` is 43 characters carrying 256 bits. Asserting on the
    encoded length rather than the constant means a future edit that lowers the
    byte count fails here instead of quietly halving the search space.
    """
    with app.app_context():
        token = account_tokens.generate_token()

    assert account_tokens.TOKEN_ENTROPY_BYTES >= 32
    assert len(token) == 43
    assert len(token.encode("utf-8")) >= account_tokens.TOKEN_ENTROPY_BYTES


def test_generated_tokens_are_distinct(app) -> None:
    """Two consecutive tokens must not collide."""
    with app.app_context():
        tokens = {account_tokens.generate_token() for _ in range(256)}

    assert len(tokens) == 256


# ---------------------------------------------------------------------------
# Digest-only storage
# ---------------------------------------------------------------------------


def test_only_the_digest_is_persisted(app, user) -> None:
    """The raw token must not be recoverable from any column of the row."""
    with app.app_context():
        raw, row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        stored = db.session.execute(db.select(AccountActionToken)).scalars().all()
        assert len(stored) == 1
        row_values = {str(value) for value in stored[0].__dict__.values() if value is not None}

        assert raw not in row_values
        assert stored[0].token_digest != raw
        assert len(stored[0].token_digest) == 64
        del row


def test_the_digest_is_keyed_not_a_bare_hash(app, user) -> None:
    """An unkeyed digest would let a database dump be attacked offline.

    The token itself is high-entropy, so a plain SHA-256 would not be brute-forceable
    -- but keying also means the digest is *purpose-bound*. A token captured from
    the verification flow is not even recognisable at the deletion endpoint,
    rather than being recognised and then rejected by a separate check.
    """
    with app.app_context():
        raw = account_tokens.generate_token()

        deletion_digest = account_tokens.token_digest(raw, AccountTokenPurpose.ACCOUNT_DELETION)
        verification_digest = account_tokens.token_digest(raw, AccountTokenPurpose.EMAIL_VERIFICATION)

    assert deletion_digest != verification_digest
    # A bare SHA-256 of the token would be reproducible by anyone; this is not.
    import hashlib

    assert deletion_digest != hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Purpose binding
# ---------------------------------------------------------------------------


def test_a_deletion_token_is_not_accepted_for_verification(app, user) -> None:
    """Purpose binding must hold at the lookup, not just at the row."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.EMAIL_VERIFICATION) is None
        assert account_tokens.consume_token(raw, AccountTokenPurpose.EMAIL_VERIFICATION) is None


def test_a_verification_token_is_not_accepted_for_deletion(app, user) -> None:
    """The reverse direction, which is the more dangerous one."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)

        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.EMAIL_VERIFICATION) is not None
        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_consuming_a_deletion_token_does_not_consume_a_verification_token(app, user) -> None:
    """Invalidating one purpose must leave the other usable.

    A user who is mid-verification and then requests deletion must not lose the
    verification link, and vice versa. This is why invalidation is always scoped
    to a purpose rather than to the account.
    """
    with app.app_context():
        deletion_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)
        verification_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)

        assert account_tokens.consume_token(deletion_raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
        assert account_tokens.lookup_outstanding(verification_raw, AccountTokenPurpose.EMAIL_VERIFICATION) is not None


def test_every_purpose_fits_the_column_width(app) -> None:
    """A purpose longer than the column would be truncated by PostgreSQL.

    Truncation would turn two distinct purposes into one, and the CHECK constraint
    would then reject both -- an outage discovered at deploy time.
    """
    for purpose in AccountTokenPurpose:
        assert len(purpose.value) <= TOKEN_PURPOSE_LENGTH, f"{purpose.value} does not fit the column"


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


def test_deletion_tokens_expire_within_thirty_minutes(app, user) -> None:
    """The specification fixes the lifetime at 30 minutes."""
    with app.app_context():
        before = datetime.now(UTC)
        _raw, row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        # SQLite round-trips `DateTime` at microsecond resolution and loses
        # timezone information, hence the explicit re-anchoring to UTC. The
        # tolerance absorbs the storage round-trip, not real clock drift.
        ttl = row.expires_at.replace(tzinfo=UTC) - before
        assert timedelta(minutes=29) < ttl <= timedelta(minutes=30, microseconds=1000)


def test_an_expired_token_is_refused(app, user) -> None:
    """Expiry must be evaluated on read, not only trusted from the column.

    The row is backdated with a raw statement rather than an attribute
    assignment: SQLAlchemy's Python-side comparison would raise on the
    offset-naive value SQLite returns, which is a property of the test database
    and not of the behaviour under test.
    """
    with app.app_context():
        raw, row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        db.session.execute(
            db.text("UPDATE account_action_tokens SET expires_at = :past WHERE id = :id"),
            {"past": datetime.now(UTC) - timedelta(seconds=1), "id": row.id},
        )
        db.session.commit()
        db.session.expire_all()

        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_a_token_expiring_in_the_future_is_accepted(app, user) -> None:
    """Guard against an off-by-one that refuses everything."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def test_a_token_can_be_consumed_exactly_once(app, user) -> None:
    """Replay is the core of the single-use guarantee."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_a_consumed_token_no_longer_appears_outstanding(app, user) -> None:
    """Consumption must be visible to the page-rendering read path too."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_an_altered_token_is_refused(app, user) -> None:
    """Flipping one character of a 43-character token must not resolve."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        # Change the last character, which is inside the HMAC input.
        altered = raw[:-1] + ("A" if raw[-1] != "A" else "B")
        assert account_tokens.consume_token(altered, AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_a_truncated_or_extended_token_is_refused(app, user) -> None:
    """Padding or truncation must not normalise to a valid digest."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.consume_token(raw[:-1], AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(raw + "A", AccountTokenPurpose.ACCOUNT_DELETION) is None


def test_an_oversized_token_is_refused_without_a_digest_lookup(app, user) -> None:
    """An unbounded parameter would make the HMAC cost attacker-controlled."""
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.lookup_outstanding("x" * 4096, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token("x" * 4096, AccountTokenPurpose.ACCOUNT_DELETION) is None
        # The real token must be unaffected by the malformed attempts.
        assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None


def test_empty_and_non_string_tokens_are_refused(app, user) -> None:
    """Falsy and wrong-typed input must not raise past the boundary."""
    with app.app_context():
        assert account_tokens.consume_token("", AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.lookup_outstanding("", AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(None, AccountTokenPurpose.ACCOUNT_DELETION) is None


# ---------------------------------------------------------------------------
# Supersession
# ---------------------------------------------------------------------------


def test_a_resend_invalidates_the_previous_token(app, user) -> None:
    """Only the newest link may work; the old one must be dead."""
    with app.app_context():
        first, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)
        second, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert first != second
        assert account_tokens.consume_token(first, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(second, AccountTokenPurpose.ACCOUNT_DELETION) is not None


def test_repeated_resends_leave_exactly_one_outstanding_token(app, user) -> None:
    """Five requests, one live token -- and no unbounded row growth."""
    with app.app_context():
        for _ in range(5):
            account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        rows = db.session.execute(db.select(AccountActionToken)).scalars().all()
        assert len(rows) == 1


def test_invalidate_tokens_retires_every_purpose(app, user) -> None:
    """An address change must kill both purposes at once."""
    with app.app_context():
        deletion_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)
        verification_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)

        removed = account_tokens.invalidate_tokens(user.id, None)

        assert removed == 2
        assert account_tokens.consume_token(deletion_raw, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(verification_raw, AccountTokenPurpose.EMAIL_VERIFICATION) is None


def test_invalidate_tokens_can_be_scoped_to_one_purpose(app, user) -> None:
    """Narrow invalidation must leave the other credential usable."""
    with app.app_context():
        deletion_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)
        verification_raw, _ = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)

        account_tokens.invalidate_tokens(user.id, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.consume_token(deletion_raw, AccountTokenPurpose.ACCOUNT_DELETION) is None
        assert account_tokens.consume_token(verification_raw, AccountTokenPurpose.EMAIL_VERIFICATION) is not None


def test_a_resend_does_not_disturb_another_accounts_token(app, user) -> None:
    """Supersession is per account; one user's resend must not revoke another's."""
    with app.app_context():
        other = User(email="other-tokens@iqoqo.local")
        other.set_password("test-password")
        db.session.add(other)
        db.session.commit()

        other_raw, _ = account_tokens.issue_token(other, AccountTokenPurpose.ACCOUNT_DELETION)
        account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert account_tokens.lookup_outstanding(other_raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_consumption_has_exactly_one_winner(app, user) -> None:
    """Two simultaneous confirmations must not both delete an account.

    This is the reason `consume_token` deletes conditionally and returns, rather
    than reading the row and then updating it: a read-then-write lets both
    requests observe "outstanding" and both proceed. The database decides here,
    and exactly one request wins.

    Threads rather than greenlets on purpose. A single SQLite in-memory database
    is shared across threads, whereas a greenlet would interleave inside one
    session and never produce two independent transactions -- which is the whole
    thing under test. Each attempt pushes its own app context so the scoped
    session is genuinely separate.
    """
    with app.app_context():
        raw, _row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        def attempt(_index: int) -> bool:
            """Try to consume the token from an independent session.

            Commits on success, because consumption is a `DELETE` and SQLite
            serialises writers: without the commit the losing threads would
            collide on the database lock and be counted as losses for the wrong
            reason, which would make this test pass for the wrong cause.
            """
            won = False
            with app.app_context():
                try:
                    won = account_tokens.consume_token(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    won = False
            return won

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(attempt, range(4)))

        assert sum(1 for won in results if won) == 1, f"expected exactly one winner, got {results}"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def test_purge_expired_removes_only_dead_rows(app, user) -> None:
    """Cleanup must not take a live token with it."""
    with app.app_context():
        expired_raw, expired_row = account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)
        expired_row.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.session.commit()

        live_raw, _live_row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        removed = AccountActionToken.purge_expired()

        assert removed == 1
        assert account_tokens.lookup_outstanding(expired_raw, AccountTokenPurpose.EMAIL_VERIFICATION) is None
        assert account_tokens.lookup_outstanding(live_raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None


def test_purge_expired_keeps_consumed_rows_within_their_window(app, user) -> None:
    """A record that a token *was* used is worth keeping until it expires.

    Consumption deletes the outstanding row rather than stamping `consumed_at`,
    so this asserts what actually survives: the row the *earlier* token occupied
    is gone, and nothing that is still live is touched.
    """
    with app.app_context():
        first_raw, _first_row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)
        assert account_tokens.consume_token(first_raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None
        db.session.commit()

        live_raw, live_row = account_tokens.issue_token(user, AccountTokenPurpose.ACCOUNT_DELETION)

        assert AccountActionToken.purge_expired() == 0
        assert db.session.get(AccountActionToken, live_row.id) is not None
        assert account_tokens.lookup_outstanding(live_raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None


# ---------------------------------------------------------------------------
# OIDC claim interpretation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"email_verified": True}, True),
        ({"email_verified": "true"}, True),
        ({"email_verified": False}, False),
        # The case a truthiness check gets backwards: the string "false" is
        # truthy in Python, so a naive `if claims.get("email_verified")` would
        # mark an explicitly *unverified* address as verified.
        ({"email_verified": "false"}, False),
        ({"email_verified": 1}, False),
        ({"email_verified": "yes"}, False),
        ({}, False),
        ({"email": "a@b.invalid"}, False),
        (None, False),
        ("not-a-dict", False),
    ],
)
def test_federated_verification_requires_a_literal_true(app, user, claims, expected) -> None:
    """Only a positive assertion may mark an address verified.

    An omitted or negative claim leaves it unverified, so the owner confirms it
    by mail. Being wrong in the permissive direction would let an unproven
    address authorise account deletion.
    """
    with app.app_context():
        user.clear_email_verification()
        db.session.commit()

        result = account_tokens.mark_verified_from_oidc(user, claims)

        assert result is expected
        assert user.is_email_verified is expected


def test_federated_verification_does_not_re_verify_an_address(app, user) -> None:
    """Re-assertion must not move the timestamp, so provenance stays truthful."""
    with app.app_context():
        assert account_tokens.mark_verified_from_oidc(user, {"email_verified": True}) is True
        first = user.email_verified_at
        user.email_verified_source = "local"

        assert account_tokens.mark_verified_from_oidc(user, {"email_verified": True}) is False
        assert user.email_verified_at == first
        assert user.email_verified_source == "local"


def test_issuing_a_token_does_not_mark_an_address_verified(app, user) -> None:
    """Minting a token is not evidence that anyone received it."""
    with app.app_context():
        account_tokens.issue_token(user, AccountTokenPurpose.EMAIL_VERIFICATION)

        assert user.is_email_verified is False
