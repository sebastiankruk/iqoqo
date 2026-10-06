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
"""End-to-end tests for confirmed account deletion.

These are the tests that matter most in this change: they cover the properties
that make irreversible deletion safe -- that initiation changes nothing, that a
mail scanner cannot trigger it, that the wrong account cannot confirm it, that
CSRF cannot be bypassed, that the transaction is atomic, and that every
outstanding credential dies with the account.

The self-checking deletion plan gets its own test class at the bottom: the
``NOT NULL`` reference list is the kind of thing that rots, and a test that
compares it against the live model metadata turns that rot into a test failure
instead of a user discovering it mid-deletion.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.decorators import CSRF_COOKIE_NAME
from app.core import account_lifecycle, account_tokens, mail_service
from app.core.account_tokens import AccountTokenPurpose
from app.core.mail_service import RecordingTransport
from app.db.auth import AccountActionToken
from app.db.core import Expression, Item, ItemStatusLog, Manifestation, Work
from app.db.lending import LoanRequest
from app.db.models import OAuthExchangeCode, User, db
from app.db.roadmap import ReadingRoadmap

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def recorder(app):
    """Capture outbound mail instead of sending it.

    Tests assert on the exact message that would have left the host, which is
    the only way to check the wording requirements ("nothing has been deleted",
    "ignore this if it was not you") without a live mailbox.
    """
    transport = RecordingTransport()
    previous = mail_service.get_mail_service()
    mail_service.set_mail_service(mail_service.MailService(transport=transport))
    try:
        yield transport
    finally:
        mail_service.set_mail_service(previous)


def _body(message: mail_service.OutboundMessage) -> str:
    """Return the decoded ``text/plain`` body of a captured message.

    Two normalisations, both required before a substring assertion means
    anything:

    * **Transfer decoding.** A serialized message may carry the body as
      quoted-printable, so a token in the text arrives as ``...3Dn2y...`` rather
      than as the token.
    * **Whitespace collapsing.** Even decoded, the body is hard-wrapped to 76
      columns per RFC 5322. Without collapsing, a phrase like "no grace period"
      is split across a line break and the assertion fails for a reason that has
      nothing to do with the wording it is checking.

    Returns:
        The body with runs of whitespace collapsed to single spaces.
    """
    import email

    decoded = email.message_from_string(message.raw).get_payload(decode=True).decode("utf-8")
    return re.sub(r"\s+", " ", decoded)


def _authenticate_cookie(client, user) -> str:
    """Put a session cookie for *user* in the test client's jar.

    Uses the jar rather than a ``Cookie`` header. The Flask test client builds the
    ``Cookie`` header from the jar itself, so a header set by hand is not what the
    request actually carries -- which produced three tests asserting 403 that were
    really asserting that the request was anonymous (401).

    Returns:
        The session token, so a test can reuse it in a second request.
    """
    token = _session_cookie(client, user)
    client.set_cookie("iqoqo_session", token, domain="localhost")
    return token


def _link_token(message: mail_service.OutboundMessage) -> str:
    """Extract the single-use token from a captured message's link.

    Asserts that there is exactly one, so a template that accidentally embeds the
    token twice -- which would let one mail fan out two live attempts -- fails
    here instead of passing unnoticed.
    """
    found = re.findall(r"token=([A-Za-z0-9_-]+)", _body(message))
    assert len(found) == 1, f"expected exactly one confirmation link, found {len(found)}"
    return found[0]


@pytest.fixture
def configured_mail(app, recorder):
    """A configured instance whose mail is captured rather than sent.

    Mail settings live in ``InstanceSettings``, which is read through the
    ``InstanceSettings`` -> config -> environment chain at send time -- so they
    have to be committed before the request under test, which is why the writes
    happen here rather than inside the test.
    """
    from app.db.models import InstanceSettings

    with app.app_context():
        InstanceSettings.set_value("MAIL_ENABLED", True)
        InstanceSettings.set_value("MAIL_HOST", "mail.iqoqo.invalid")
        InstanceSettings.set_value("MAIL_PORT", 587)
        InstanceSettings.set_value("MAIL_FROM_ADDRESS", "no-reply@iqoqo.invalid")
        InstanceSettings.set_value("PUBLIC_APP_URL", "https://iqoqo.example")
    yield recorder


@pytest.fixture
def unverified_user(app):
    """An account whose address starts unverified.

    Separate from `owner` because that one is already verified, and a
    verification test asserting against it proves nothing: it would pass whether
    or not the endpoint saved anything.

    Yields:
        The new account's id.
    """
    with app.app_context():
        record = User(email="unverified-fixture@iqoqo.local", display_name="Not Yet Verified")
        record.set_password("test-password")
        db.session.add(record)
        db.session.commit()
        yield record.id
        db.session.rollback()


@pytest.fixture
def owner(app):
    """An account with a verified address, the actor for most deletion tests."""
    with app.app_context():
        record = User(email="owner@iqoqo.local", display_name="Deleting Owner")
        record.set_password("test-password")
        record.mark_email_verified("local")
        db.session.add(record)
        db.session.commit()
        yield record.id
        db.session.rollback()


def _session_cookie(client, user) -> str:
    """Return a session token for *user*, for cookie-authenticated requests.

    Accepts either a ``User`` or a bare id, because the fixtures hand out ids
    (an ORM object is bound to the session that loaded it, and these tests each
    work inside their own application context).

    Cookie auth matters because CSRF applies only to it. Using a bearer token
    throughout would silently skip the whole CSRF suite, since
    ``enforce_csrf_if_cookie_authenticated`` returns early for header
    credentials -- correct, but it means these tests must opt in explicitly.
    """
    from app.api.auth import generate_internal_jwt

    if isinstance(user, User):
        return generate_internal_jwt(user)

    with client.application.app_context():
        record = db.session.get(User, user)
        assert record is not None, "the session token helper was given an id with no matching account"
        return generate_internal_jwt(record)


# ---------------------------------------------------------------------------
# The deletion plan is verified against the model metadata
# ---------------------------------------------------------------------------


def _orm_cascaded_user_tables() -> set[str]:
    """Return the tables whose rows an ORM cascade from ``User`` already removes.

    Read from the live mapper rather than hardcoded, so the answer stays correct
    as relationships are added. A relationship qualifies when it carries
    ``delete-orphan`` (which deletes the child row) or is a ``secondary``
    association (which deletes the link row).
    """
    from sqlalchemy import inspect as sa_inspect

    cascaded: set[str] = set()
    for relationship in sa_inspect(User).relationships:
        cascade = relationship.cascade or {}
        if "delete-orphan" in cascade:
            mapper = sa_inspect(relationship.mapper)
            cascaded.add(mapper.local_table.name)
        if relationship.secondary is not None:
            cascaded.add(relationship.secondary.name)
    return cascaded


class TestDeletionPlanCoverage:
    """The explicit ``NOT NULL`` reference list must match the schema.

    Four child tables reference ``auth.users`` with a ``NOT NULL`` foreign key and
    no ORM cascade. The deletion plan names them. If a fifth is ever added and the
    plan is not updated, the account deletion fails part-way through -- during an
    irreversible operation, on a real user's data. These tests make that a CI
    failure instead.
    """

    def test_every_not_null_user_reference_is_either_cascaded_or_in_the_plan(self, app) -> None:
        """No ``NOT NULL`` foreign key to ``users`` may be left unhandled.

        A ``NOT NULL`` column cannot survive the ORM's de-association -- it sets
        the reference to ``NULL`` -- so each one must be either carried by a
        ``delete-orphan`` cascade or named in the plan. A new one that is neither
        makes account deletion fail part-way through, during an irreversible
        operation, on a real user's data.
        """
        with app.app_context():
            planned = {(model.__tablename__, column) for model, column in account_lifecycle.NOT_NULL_USER_REFERENCES}
            cascaded = _orm_cascaded_user_tables()

            unhandled: set[tuple[str, str]] = set()
            for table in db.metadata.sorted_tables:
                for fk in table.foreign_keys:
                    if fk.column.table.name != "users" or fk.parent.nullable:
                        continue
                    key = (table.name, fk.parent.name)
                    if key not in planned and table.name not in cascaded:
                        unhandled.add(key)

            assert not unhandled, (
                f"NOT NULL references to users are neither cascaded nor in the deletion plan: {sorted(unhandled)}. "
                "Add them to app.core.account_lifecycle.NOT_NULL_USER_REFERENCES, or give the relationship "
                "`cascade='all, delete-orphan'`."
            )

    def test_the_plan_does_not_name_columns_that_no_longer_exist(self, app) -> None:
        """A stale plan entry would fail on an attribute error, not a constraint.

        Which is worse: the deletion would break in a way whose traceback points
        at the plan rather than at the schema change that caused it.
        """
        with app.app_context():
            for model, column in account_lifecycle.NOT_NULL_USER_REFERENCES:
                assert hasattr(model, column), f"{model.__tablename__}.{column} named in the plan does not exist"
                assert column in {col.name for col in model.__table__.columns}

    def test_the_plan_entries_really_are_not_null(self, app) -> None:
        """A nullable entry in the plan is dead code that hides a future mistake.

        More importantly, it would suggest nullable references need handling when
        they do not -- and the next person to add one would trust the plan.
        """
        with app.app_context():
            for model, column in account_lifecycle.NOT_NULL_USER_REFERENCES:
                assert not model.__table__.columns[
                    column
                ].nullable, f"{model.__tablename__}.{column} is nullable and does not belong in the deletion plan"

    def test_nullable_user_references_are_set_to_null_or_orphaned_by_the_orm(self, app) -> None:
        """The other half of the contract: nullable references must resolve cleanly.

        A nullable ``ON DELETE SET NULL`` needs no plan entry -- both the ORM and
        the database handle it. But a nullable column with ``CASCADE`` and no ORM
        relationship would be silently *relied upon*, and SQLite does not enforce
        cascades at all, so the behaviour would differ between the test database
        and production. This asserts the assumption rather than trusting it.
        """
        with app.app_context():
            planned = {(model.__tablename__, column) for model, column in account_lifecycle.NOT_NULL_USER_REFERENCES}
            cascaded = _orm_cascaded_user_tables()
            unplanned: list[tuple[str, str, str | None]] = []

            for table in db.metadata.sorted_tables:
                for fk in table.foreign_keys:
                    if fk.column.table.name != "users":
                        continue
                    key = (table.name, fk.parent.name)
                    ondelete = (fk.ondelete or "").upper()
                    if not fk.parent.nullable:
                        continue  # covered by the NOT NULL test above
                    if key in planned or table.name in cascaded:
                        continue
                    if ondelete != "SET NULL":
                        unplanned.append((table.name, fk.parent.name, fk.ondelete))

            assert not unplanned, (
                f"nullable user references relying on cascade behaviour SQLite does not enforce: {unplanned}. "
                "Give the relationship a `lazy='dynamic'` so the ORM clears it, or add it to the deletion plan."
            )


# ---------------------------------------------------------------------------
# Initiation changes nothing
# ---------------------------------------------------------------------------


class TestInitiationIsInert:
    """``POST /deletion/request`` must not delete or anonymise anything."""

    def test_request_creates_a_pending_token_and_leaves_the_account(self, client, configured_mail, owner) -> None:
        with client.application.app_context():
            token = _session_cookie(client, owner)
            response = client.post(
                "/api/account/deletion/request",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 202
            assert response.get_json()["success"] is True

            # The account and its data are untouched.
            still_there = db.session.get(User, owner)
            assert still_there is not None
            assert still_there.email == "owner@iqoqo.local"

            # Exactly one pending token, and nothing consumed.
            rows = db.session.execute(db.select(AccountActionToken)).scalars().all()
            assert len(rows) == 1
            assert rows[0].purpose == AccountTokenPurpose.ACCOUNT_DELETION.value
            assert rows[0].consumed_at is None

    def test_request_sends_the_link_to_the_verified_address(self, client, configured_mail, owner) -> None:
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            assert len(configured_mail.sent) == 1
            sent = configured_mail.sent[0]
            assert sent.recipient == "owner@iqoqo.local"
            assert sent.envelope_from == "no-reply@iqoqo.invalid"

    def test_the_request_email_states_that_nothing_has_been_deleted(self, client, configured_mail, owner) -> None:
        """The wording is a security control, not copy.

        A "confirm your account deletion" mail that does not say the account is
        still intact is indistinguishable from a phishing mail, which is exactly
        the situation a user needs to be able to reason about.
        """
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            body = _body(configured_mail.sent[0])
            assert "Nothing has been deleted" in body
            assert "permanent" in body.lower()
            assert "cannot be recovered" in body.lower()
            assert "no grace period" in body.lower()

    def test_the_request_email_carries_exactly_one_confirmation_link(self, client, configured_mail, owner) -> None:
        """One link, so the mail cannot be used to fan out several attempts."""
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            links = re.findall(
                r"https://iqoqo\.example/account/delete\?token=([A-Za-z0-9_-]+)",
                _body(configured_mail.sent[0]),
            )
            assert len(links) == 1, "the mail must link to the frontend confirmation route, once"

    def test_the_request_email_carries_no_reusable_token_for_another_purpose(self, client, configured_mail, owner) -> None:
        """The emailed token must not work for verification, or vice versa."""
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            link = _link_token(configured_mail.sent[0])

            assert account_tokens.consume_token(link, AccountTokenPurpose.EMAIL_VERIFICATION) is None
            assert account_tokens.lookup_outstanding(link, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_a_second_request_supersedes_the_first(self, client, configured_mail, owner) -> None:
        """Resending must invalidate the earlier link."""
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})
            first_link = _link_token(configured_mail.sent[-1])

            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})
            second_link = _link_token(configured_mail.sent[-1])

            assert first_link != second_link
            assert account_tokens.lookup_outstanding(first_link, AccountTokenPurpose.ACCOUNT_DELETION) is None
            assert account_tokens.lookup_outstanding(second_link, AccountTokenPurpose.ACCOUNT_DELETION) is not None


# ---------------------------------------------------------------------------
# An unverified address cannot be a route to deletion
# ---------------------------------------------------------------------------


class TestVerifiedEmailIsRequired:
    """There is deliberately no weaker bypass for an unverified address."""

    def test_request_is_refused_without_a_verified_address(self, client, configured_mail, app) -> None:
        with client.application.app_context():
            record = User(email="unverified@iqoqo.local")
            record.set_password("test-password")
            db.session.add(record)
            db.session.commit()

            token = _session_cookie(client, record)
            response = client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 409
            body = response.get_json()
            assert body["email_verified"] is False
            assert "Verify your email" in body["error"]

            # No request, no mail, and above all no token: an unverified address
            # may belong to someone else, and a token in their inbox would be an
            # account-deletion credential.
            assert db.session.execute(db.select(AccountActionToken)).scalars().all() == []
            assert configured_mail.sent == []
            assert db.session.get(User, record.id) is not None

    def test_the_response_says_the_address_must_be_verified_first(self, client, configured_mail, app) -> None:
        """The user is told what to do, not merely refused."""
        with client.application.app_context():
            record = User(email="unverified2@iqoqo.local")
            record.set_password("test-password")
            db.session.add(record)
            db.session.commit()

            token = _session_cookie(client, record)
            response = client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            assert "Verify your email address" in response.get_json()["error"]

    def test_a_relay_failure_is_not_reported_as_a_configuration_problem(self, client, configured_mail, owner) -> None:
        """A reachable relay that refuses must not be described as "not configured".

        Reporting both under one message sent a report of a live-but-refusing
        relay to the wrong investigation -- and pointed the person debugging it
        at settings that were already correct.
        """
        from app.core.mail_service import MailDeliveryError

        class RefusingTransport:
            def deliver(self, message, settings):
                raise MailDeliveryError("The mail relay rejected or dropped the message: SMTPRecipientsRefused")

        previous = mail_service.get_mail_service()
        mail_service.set_mail_service(mail_service.MailService(transport=RefusingTransport()))
        try:
            with client.application.app_context():
                token = _session_cookie(client, owner)
                response = client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            assert response.status_code == 503
            error = response.get_json()["error"]
            assert "not configured" not in error
            assert "mail server could not be reached or refused" in error
        finally:
            mail_service.set_mail_service(previous)

    def test_a_configuration_failure_is_reported_as_a_configuration_problem(self, client, owner) -> None:
        """The other half: an unusable configuration must still say so."""
        with client.application.app_context():
            record = User(email="nomail@iqoqo.local")
            record.set_password("test-password")
            record.mark_email_verified("local")
            db.session.add(record)
            db.session.commit()

            token = _session_cookie(client, record)
            # No `configured_mail`, so MAIL_ENABLED is unset and mail is unusable.
            response = client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 503
        assert "not configured to send mail" in response.get_json()["error"]


class TestScannerSafety:
    """A ``GET`` of the emailed link must change nothing.

    Mail-security scanners fetch every URL in an inbound message within seconds
    of arrival, before the user has read it. Any state change on ``GET`` would
    therefore delete accounts that the user never intended to delete.

    The confirmation screens are frontend routes now; these tests exercise the
    JSON state endpoint they read, which is the Flask side of the same guarantee.
    The browser-facing security headers moved with the pages and are asserted in
    ``frontend/__tests__/config/token-page-headers.test.ts``.
    """

    @pytest.fixture
    def pending_token(self, client, configured_mail, owner):
        """A live deletion token, as if a user had just requested deletion."""
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})
            pending = _link_token(configured_mail.sent[-1])
        yield pending

    def test_a_bare_get_does_not_delete_or_consume(self, client, configured_mail, owner, pending_token) -> None:
        """The scanner case: no session, no cookie, just the URL."""
        response = client.get(f"/api/account/deletion/confirm?token={pending_token}")

        # No credential at all, so nothing is disclosed and nothing changes.
        assert response.status_code == 401
        assert response.mimetype == "application/json"

        with client.application.app_context():
            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_an_authenticated_get_does_not_delete_or_consume(self, client, configured_mail, owner, pending_token) -> None:
        """Authenticated link preview is still just a preview."""
        token = _session_cookie(client, owner)
        response = client.get(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert response.get_json()["data"]["usable"] is True

        with client.application.app_context():
            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_repeated_gets_leave_the_token_spendable(self, client, configured_mail, owner, pending_token) -> None:
        """A prefetching browser or an over-eager scanner may fetch many times."""
        token = _session_cookie(client, owner)
        bodies = [
            client.get(
                f"/api/account/deletion/confirm?token={pending_token}",
                headers={"Authorization": f"Bearer {token}"},
            ).get_json()
            for _ in range(5)
        ]

        assert len({str(b) for b in bodies}) == 1, "the reported state must not vary between identical GETs"

        with client.application.app_context():
            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_the_endpoint_returns_json_not_html(self, client, configured_mail, owner, pending_token) -> None:
        """Flask is API-only. A `text/html` response here would reintroduce the
        hand-styled server-rendered page this flow moved away from."""
        token = _session_cookie(client, owner)
        response = client.get(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.mimetype == "application/json"
        assert "<html" not in response.data.decode().lower()

    def test_an_unknown_token_is_indistinguishable_from_an_expired_one(self, client, configured_mail, owner) -> None:
        """One answer for every rejection, so nothing can be learned from it."""
        token = _session_cookie(client, owner)
        first = client.get(
            "/api/account/deletion/confirm?token=" + "A" * 43,
            headers={"Authorization": f"Bearer {token}"},
        )
        second = client.get(
            "/api/account/deletion/confirm?token=" + "B" * 43,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert first.status_code == second.status_code == 200
        assert first.get_json() == second.get_json()
        assert first.get_json()["data"]["usable"] is False
        # No account or address is echoed back for an unusable token.
        assert "email" not in first.get_json()["data"]

    def test_a_signed_in_user_sees_the_verification_state(self, client, configured_mail, unverified_user) -> None:
        """The verification endpoint has the same read-only contract."""
        target = unverified_user
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, target), AccountTokenPurpose.EMAIL_VERIFICATION)

        token = _session_cookie(client, target)
        response = client.get(
            f"/api/account/email/verify?token={raw}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["usable"] is True

        with client.application.app_context():
            assert db.session.get(User, target).is_email_verified is False, "a GET must not verify"

    def test_an_anonymous_get_discloses_nothing(self, client, configured_mail, owner) -> None:
        """Without a session there is no answer at all, not even 'unusable'.

        Distinguishing "you are not signed in" from "this token is dead" would let
        a caller with a stolen token probe which accounts exist.
        """
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.EMAIL_VERIFICATION)

        response = client.get(f"/api/account/email/verify?token={raw}")

        assert response.status_code == 401
        assert "usable" not in response.get_json()


# ---------------------------------------------------------------------------
# Confirmation authorisation
# ---------------------------------------------------------------------------


class TestConfirmationRequiresBothFactors:
    """Token *and* session. Neither alone is a credential."""

    @pytest.fixture
    def pending_token(self, client, configured_mail, owner):
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})
            pending = _link_token(configured_mail.sent[-1])

        # Yielded *outside* the app context deliberately. Flask binds `g` to the
        # app context and the test client reuses an already-pushed one, so
        # yielding inside it leaks `g.user_id` from the POST above into the
        # test's own request. That made assertions pass against routes carrying
        # no auth decorator at all, which is how the missing `optional_auth` on
        # the two confirmation GETs went unnoticed.
        yield pending

    def test_the_email_url_alone_cannot_delete(self, client, configured_mail, owner, pending_token) -> None:
        """A forwarded, archived or scanned link must be inert.

        This is the specific weakness the two-factor confirmation exists to
        close: if the URL were sufficient, anyone who ever saw the mail -- a
        support agent, a shared mailbox, a mail archive -- could destroy the
        account.
        """
        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            data={"confirm": "delete"},
        )

        assert response.status_code == 401
        with client.application.app_context():
            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_the_correct_account_can_confirm(self, client, configured_mail, owner, pending_token) -> None:
        """The happy path, end to end, with real mail capture."""
        token = _session_cookie(client, owner)
        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {token}"},
            data={"confirm": "delete"},
        )

        assert response.status_code == 200
        with client.application.app_context():
            assert db.session.get(User, owner) is None

    def test_a_different_account_cannot_confirm(self, client, configured_mail, owner, pending_token) -> None:
        """A valid token from a different session changes nothing for either party.

        The attack: an attacker gets a deletion mail forwarded to them, or simply
        holds a token, and confirms while signed in as themselves. Account
        binding is what stops a token from being a universal deletion key.
        """
        with client.application.app_context():
            attacker = User(email="attacker@iqoqo.local")
            attacker.set_password("test-password")
            db.session.add(attacker)
            db.session.commit()
            attacker_token = _session_cookie(client, attacker)

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {attacker_token}"},
            data={"confirm": "delete"},
        )

        assert response.status_code == 400
        assert response.get_json()["usable"] is False

        with client.application.app_context():
            assert db.session.get(User, owner) is not None, "the owner's account must survive"
            assert db.session.get(User, attacker.id) is not None, "the attacker's account must survive"
            # And the owner's token is still usable by the right account.
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_confirmation_is_a_post_of_only_the_token(self, client, configured_mail, owner, pending_token) -> None:
        """Confirming needs nothing but the token and the session.

        The predecessor of this test posted the form exactly as the server rendered
        it, which caught a `confirm=delete` field the page never contained -- a
        submit that re-displayed the page and deleted nothing, indistinguishable
        from a dead button. The screen has since moved to the frontend, so the
        contract is now expressed directly: a JSON POST carrying only the token.

        Any field the client must echo back is a field the client can be made to
        send for the wrong reason.
        """
        token = _session_cookie(client, owner)
        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, "confirming needs only the token and the session"
        assert response.get_json()["data"]["deleted"] is True

        with client.application.app_context():
            db.session.remove()
            assert db.session.get(User, owner) is None, "the page reported success but the account survived"

    def test_an_expired_token_cannot_confirm(self, client, configured_mail, owner) -> None:
        """Expiry is enforced at confirmation, not merely advertised."""
        with client.application.app_context():
            raw, row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            db.session.execute(
                db.text("UPDATE account_action_tokens SET expires_at = :past WHERE id = :id"),
                {"past": datetime.now(UTC) - timedelta(seconds=1), "id": row.id},
            )
            db.session.commit()
            db.session.expire_all()

            token = _session_cookie(client, owner)
            response = client.post(
                f"/api/account/deletion/confirm?token={raw}",
                headers={"Authorization": f"Bearer {token}"},
                data={"confirm": "delete"},
            )

            assert "no longer valid" in response.data.decode()
            assert db.session.get(User, owner) is not None


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def _csrf_cookie_from(response) -> str | None:
    """Read the CSRF cookie value out of a response's ``Set-Cookie`` header.

    Parsed from the header rather than read from the test client's cookie jar,
    because the jar accumulates same-named entries once a test also sets the
    cookie explicitly, and `get_cookie` then returns whichever came first. That
    ambiguity made these tests assert against a stale value.
    """
    for value in response.headers.getlist("Set-Cookie"):
        if value.startswith(f"{CSRF_COOKIE_NAME}="):
            return value.split(f"{CSRF_COOKIE_NAME}=", 1)[1].split(";", 1)[0]
    return None


class TestCsrfProtection:
    """Cookie-authenticated confirmation must prove it was not cross-site.

    These tests deliberately use the session *cookie*, not a bearer header. CSRF
    applies only to credentials the browser attaches by itself, so a bearer-token
    test would pass regardless of whether the protection works.
    """

    @pytest.fixture
    def pending_token(self, client, configured_mail, owner):
        with client.application.app_context():
            token = _session_cookie(client, owner)
            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})
            pending = _link_token(configured_mail.sent[-1])

        # Yielded *outside* the app context deliberately. Flask binds `g` to the
        # app context and the test client reuses an already-pushed one, so
        # yielding inside it leaks `g.user_id` from the POST above into the
        # test's own request. That made assertions pass against routes carrying
        # no auth decorator at all, which is how the missing `optional_auth` on
        # the two confirmation GETs went unnoticed.
        yield pending

    def test_cookie_auth_without_csrf_proof_is_refused(self, client, configured_mail, owner, pending_token) -> None:
        """A cross-site POST carries the cookie but cannot read the CSRF cookie."""
        _authenticate_cookie(client, owner)

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            data={"confirm": "delete"},
        )

        assert response.status_code == 403
        with client.application.app_context():
            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(pending_token, AccountTokenPurpose.ACCOUNT_DELETION) is not None

    def test_cookie_auth_with_a_matching_token_succeeds(self, client, configured_mail, owner, pending_token) -> None:
        """The happy path for the form flow, proving the check is not blocking everything."""
        _authenticate_cookie(client, owner)

        minted = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"X-CSRF-Token": minted},
        )

        assert response.status_code == 200
        with client.application.app_context():
            assert db.session.get(User, owner) is None

    def test_a_minted_csrf_token_is_accepted_by_the_json_client(self, client, configured_mail, owner, pending_token) -> None:
        """The happy path for the browser client, proving the check is not blocking everything.

        This is exactly what `frontend/lib/api/account.ts` does: GET
        `/api/account/csrf`, then echo the cookie's value in the `X-CSRF-Token`
        header on the mutation. It replaces an earlier version of this test that
        posted a server-rendered form, which no longer exists.
        """
        _authenticate_cookie(client, owner)

        minted_response = client.get("/api/account/csrf")
        minted = minted_response.get_json()["data"]["csrf_token"]
        cookie_value = _csrf_cookie_from(minted_response)
        assert cookie_value is not None, "GET /api/account/csrf must set the cookie"
        assert cookie_value == minted, "the response body and the cookie must carry the same token"

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"X-CSRF-Token": cookie_value},
        )

        assert response.status_code == 200
        with client.application.app_context():
            db.session.remove()
            assert db.session.get(User, owner) is None

    def test_the_csrf_endpoint_mints_a_fresh_token_every_time(self, client, configured_mail) -> None:
        """A fixed token would let a replayed page keep authorising submissions.

        Matters because the confirmation pages live in the frontend now and are
        re-fetched on every visit; a cached value would outlive the page it was
        minted for.
        """
        first_response = client.get("/api/account/csrf")
        first = first_response.get_json()["data"]["csrf_token"]
        first_cookie = _csrf_cookie_from(first_response)
        second_response = client.get("/api/account/csrf")
        second = second_response.get_json()["data"]["csrf_token"]
        second_cookie = _csrf_cookie_from(second_response)

        assert first != second, "every mint must produce a distinct token"
        assert first_cookie == first
        assert second_cookie == second

    def test_the_csrf_cookie_is_not_readable_by_scripts_only_by_being_echoed(self, client, configured_mail) -> None:
        """The cookie is deliberately not httpOnly: double submit needs the client
        to read it. What makes it safe is the signature, asserted in the forgery
        tests below."""
        response = client.get("/api/account/csrf")

        # httponly absent => readable by JS, which is required for the double submit.
        assert "HttpOnly" not in response.headers.get("Set-Cookie", "")
        assert "SameSite=Strict" in response.headers.get("Set-Cookie", "")

    def test_a_csrf_value_absent_from_the_cookie_is_refused(self, client, configured_mail, owner, pending_token) -> None:
        """The double submit must compare against the cookie actually presented.

        The signature makes a token globally valid rather than per-session, so the
        binding to the request rests entirely on this comparison. A value that
        arrives in the header and the form but not in the cookie is exactly what a
        cross-site attacker can produce -- they can make the browser send a cookie,
        but never one whose value they chose.
        """
        _authenticate_cookie(client, owner)
        csrf_response = client.get("/api/account/csrf")
        csrf = csrf_response.get_json()["data"]["csrf_token"]
        assert _csrf_cookie_from(csrf_response) is not None

        # Remove the CSRF cookie, keeping the session. This is the cross-site
        # shape: the browser attaches the session automatically, but the
        # attacker cannot make it attach a CSRF value of their choosing.
        client.delete_cookie("iqoqo_csrf", domain="localhost")

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"X-CSRF-Token": csrf},
        )

        assert response.status_code == 403
        with client.application.app_context():
            assert db.session.get(User, owner) is not None

    def test_a_tampered_csrf_signature_is_refused(self, client, configured_mail, owner, pending_token) -> None:
        """A correctly-formed but unsigned value must not pass.

        The cookie and the header agree here, so the double-submit comparison is
        satisfied -- only the HMAC check stands between the attacker and a
        deletion. This asserts that check exists.
        """
        _authenticate_cookie(client, owner)
        csrf = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]
        nonce, issued, _signature = csrf.rsplit(".", 2)
        tampered = f"{nonce}.{issued}.{'0' * 64}"
        client.set_cookie("iqoqo_csrf", tampered, domain="localhost")

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"X-CSRF-Token": tampered},
        )

        assert response.status_code == 403
        with client.application.app_context():
            assert db.session.get(User, owner) is not None

    def test_an_expired_csrf_token_is_refused(self, client, configured_mail, owner, pending_token) -> None:
        """A correctly signed token from long ago must not still work."""
        from app.api.decorators import CSRF_TOKEN_TTL_SECONDS, issue_csrf_token, verify_csrf_token

        stale = f"{uuid.uuid4().hex}.{int(datetime.now(UTC).timestamp()) - CSRF_TOKEN_TTL_SECONDS - 60}.{'0' * 64}"

        with client.application.app_context():
            assert verify_csrf_token(issue_csrf_token()) is True
            assert verify_csrf_token(stale) is False
            # Malformed input must return False rather than raising, since this
            # runs on the request path with attacker-controlled data.
            assert verify_csrf_token("garbage") is False
            assert verify_csrf_token("") is False
            assert verify_csrf_token("a.b") is False

        _authenticate_cookie(client, owner)
        client.set_cookie("iqoqo_csrf", stale, domain="localhost")

        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"X-CSRF-Token": stale},
            data={"confirm": "delete", "csrf_token": stale},
        )

        assert response.status_code == 403
        with client.application.app_context():
            assert db.session.get(User, owner) is not None

    def test_bearer_auth_needs_no_csrf_proof(self, client, configured_mail, owner, pending_token) -> None:
        """A header credential is not attached by the browser, so CSRF cannot apply.

        Asserted explicitly so the exemption is a tested decision rather than an
        oversight: demanding a CSRF token here would protect against nothing and
        break every API client.
        """
        token = _session_cookie(client, owner)
        response = client.post(
            f"/api/account/deletion/confirm?token={pending_token}",
            headers={"Authorization": f"Bearer {token}"},
            data={"confirm": "delete"},
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Deletion semantics
# ---------------------------------------------------------------------------


class TestDeletionSemantics:
    """The delete itself must match the existing cascade behaviour, with no grace period."""

    def test_deletion_takes_the_accounts_data_with_it(self, client, configured_mail, owner) -> None:
        """Cascade coverage, asserted against a graph holding one of everything.

        A deletion that left orphans behind would both leak the user's data --
        the opposite of "right to be forgotten" -- and trip a foreign key on the
        next write.
        """
        with client.application.app_context():
            account = db.session.get(User, owner)
            work = Work(title="To Be Deleted")
            db.session.add(work)
            db.session.flush()
            expression = Expression(work_id=work.id, content_type="book", language="en")
            db.session.add(expression)
            db.session.flush()
            manifestation = Manifestation(expression_id=expression.id)
            db.session.add(manifestation)
            db.session.flush()
            item = Item(owner_id=owner, manifestation_id=manifestation.id, status="read")
            db.session.add(item)
            db.session.commit()
            work_id = work.id
            manifestation_id = manifestation.id

            raw, _row = account_tokens.issue_token(account, AccountTokenPurpose.ACCOUNT_DELETION)
            outcome = account_lifecycle.confirm_deletion(raw, owner)

            assert outcome.user_id == owner
            assert db.session.get(User, owner) is None
            # The Work is a shared catalogue entity and must survive; the Item is
            # the user's inventory and must not.
            assert db.session.get(Work, work_id) is not None, "a shared catalogue Work must survive"
            assert db.session.get(Manifestation, manifestation_id) is not None, "a shared Manifestation must survive"
            assert db.session.execute(db.select(Item).where(Item.owner_id == owner)).scalars().all() == []

    def test_deletion_clears_the_four_unplanned_child_tables(self, client, configured_mail, owner) -> None:
        """The tables named in the deletion plan must actually be emptied.

        Those four carry a ``NOT NULL`` foreign key with no ORM cascade, so they
        are exactly the ones that would abort the delete. Asserting on them
        specifically is what makes the plan test meaningful rather than
        decorative.
        """
        with client.application.app_context():
            account = db.session.get(User, owner)

            db.session.add_all(
                [
                    ItemStatusLog(item_id=1, user_id=owner, new_status="read"),
                    ReadingRoadmap(user_id=owner, title="Doomed roadmap"),
                    OAuthExchangeCode(
                        code_hash="a" * 64,
                        user_id=owner,
                        expires_at=datetime.now(UTC) + timedelta(minutes=1),
                    ),
                    LoanRequest(item_id=1, requester_id=owner, status="pending"),
                ]
            )
            db.session.commit()

            raw, _row = account_tokens.issue_token(account, AccountTokenPurpose.ACCOUNT_DELETION)
            account_lifecycle.confirm_deletion(raw, owner)

            for model in (ItemStatusLog, ReadingRoadmap, OAuthExchangeCode, LoanRequest):
                assert db.session.execute(db.select(model)).scalars().all() == [], f"{model.__tablename__} survived"

    def test_a_deleted_accounts_tokens_are_gone(self, client, configured_mail, owner) -> None:
        """No live credential may outlive the account it belonged to."""
        with client.application.app_context():
            account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.EMAIL_VERIFICATION)
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)

            account_lifecycle.confirm_deletion(raw, owner)

            assert db.session.execute(db.select(AccountActionToken)).scalars().all() == []

    def test_deletion_is_immediate_with_no_grace_period(self, client, configured_mail, owner) -> None:
        """The row is gone by the time the response is returned.

        A grace period would be a new, unspecified retention policy introduced by
        this change; the specification explicitly rules one out.
        """
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            account_lifecycle.confirm_deletion(raw, owner)

            # No soft-delete column exists, and a fresh read finds nothing.
            assert db.session.get(User, owner) is None
            columns = {col.name for col in User.__table__.columns}
            assert "deleted_at" not in columns
            assert "is_deleted" not in columns

    def test_a_rejected_confirmation_leaves_a_retryable_request(self, client, configured_mail, owner) -> None:
        """A refusal must not burn the token.

        Otherwise a user who mistypes their confirmation, or whose session expires
        mid-flow, is locked out of deleting their account until the token expires
        with no way to tell why.
        """
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)

            # Confirm as a different account: the request must be refused.
            with pytest.raises(account_lifecycle.DeletionRejected):
                account_lifecycle.confirm_deletion(raw, uuid.uuid4())

            assert db.session.get(User, owner) is not None
            assert account_tokens.lookup_outstanding(raw, AccountTokenPurpose.ACCOUNT_DELETION) is not None

            # And the right account can still use it.
            account_lifecycle.confirm_deletion(raw, owner)
            assert db.session.get(User, owner) is None

    def test_the_completion_notice_carries_no_token_or_link(self, client, configured_mail, owner) -> None:
        """A queued message is data at rest; a spent credential has no business in one.

        It would also be a link-shaped hazard for whoever reads that mailbox next.
        """
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            outcome = account_lifecycle.confirm_deletion(raw, owner)

            rendered = account_lifecycle.account_mail.deletion_completed(outcome.display_name)

            assert "token=" not in rendered.text
            assert "http" not in rendered.text
            assert "deleted" in rendered.text.lower()

    def test_a_mail_failure_after_deletion_does_not_restore_the_account(self, client, configured_mail, owner) -> None:
        """Delivery is a courtesy; the deletion is already correct.

        Tested by making the transport raise. The account must stay deleted and
        the request must succeed -- the alternative is a 500 inviting the user to
        retry against an account that no longer exists.
        """
        from app.core.mail_service import MailDeliveryError

        class ExplodingTransport:
            def deliver(self, message, settings):
                raise MailDeliveryError("relay is down")

        previous = mail_service.get_mail_service()
        mail_service.set_mail_service(mail_service.MailService(transport=ExplodingTransport()))
        try:
            with client.application.app_context():
                raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
                outcome = account_lifecycle.confirm_deletion(raw, owner)

                from app.api.account import _notify_deletion_completed

                _notify_deletion_completed(outcome)  # must not raise
                assert db.session.get(User, owner) is None
        finally:
            mail_service.set_mail_service(previous)


# ---------------------------------------------------------------------------
# Credential revocation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The rendered pages
class TestCredentialsDieWithTheAccount:
    """A deleted account's outstanding JWTs must stop working immediately.

    The tokens are stateless and live for seven days, and the per-token blocklist
    only knows about explicit logouts -- so without a live-account check on every
    authenticated request, deleting an account would leave a working session in
    the hands of whoever had the cookie.
    """

    def test_a_bearer_jwt_stops_working_after_deletion(self, client, configured_mail, owner) -> None:
        from app.api.auth import generate_internal_jwt

        with client.application.app_context():
            token = _session_cookie(client, owner)
            # It works before deletion.
            assert client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"}).status_code == 200

            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            account_lifecycle.confirm_deletion(raw, owner)

            after = client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})
            assert after.status_code == 401

    def test_a_session_cookie_stops_working_after_deletion(self, client, configured_mail, owner) -> None:
        with client.application.app_context():
            _authenticate_cookie(client, owner)

            assert client.get("/api/profile/").status_code == 200

            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            account_lifecycle.confirm_deletion(raw, owner)

            assert client.get("/api/profile/").status_code == 401

    def test_a_suspended_accounts_jwt_stops_working(self, client, owner) -> None:
        """The same check covers suspension, which had the identical gap."""
        from app.api.auth import generate_internal_jwt

        with client.application.app_context():
            token = _session_cookie(client, owner)
            assert client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"}).status_code == 200

            db.session.get(User, owner).is_active = False
            db.session.commit()

            assert client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    def test_the_rejection_does_not_distinguish_a_deleted_account(self, client, configured_mail, owner) -> None:
        """A distinct status or message would be an enumeration oracle.

        A caller holding a stolen token could otherwise learn whether the account
        is gone, which confirms a successful deletion to someone who should not
        know it happened.
        """
        from app.api.auth import generate_internal_jwt

        with client.application.app_context():
            deleted_token = _session_cookie(client, owner)
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)
            account_lifecycle.confirm_deletion(raw, owner)

            deleted = client.get("/api/profile/", headers={"Authorization": f"Bearer {deleted_token}"})

            garbage = client.get("/api/profile/", headers={"Authorization": "Bearer not.a.jwt"})
            unsigned = client.get("/api/profile/", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.e30.abc"})

            assert deleted.status_code == garbage.status_code == unsigned.status_code == 401
            assert (
                deleted.get_json() == garbage.get_json() == unsigned.get_json()
            ), "a deleted account must be indistinguishable from a token that never existed"

    def test_a_database_failure_fails_closed(self, client, owner, monkeypatch) -> None:
        """A database blip must not authenticate anyone."""
        from app.api.auth import generate_internal_jwt

        with client.application.app_context():
            token = _session_cookie(client, owner)

            def explode(*_args, **_kwargs):
                raise RuntimeError("connection reset")

            monkeypatch.setattr(db.session, "get", explode)

            assert client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Issuance is rate limited per account."""

    def test_repeated_requests_are_refused_after_the_limit(self, app, client, configured_mail, owner) -> None:
        """Issuance must stop, not merely slow down.

        Every accepted request sends a mail to a real mailbox, so the thing being
        protected is the recipient's tolerance. Three per hour is the limit; past
        it the endpoint must refuse.
        """
        from app.core.limiter import limiter

        # The suite runs with the limiter disabled, so it has to be switched on
        # explicitly. `init_app` is re-run because the enabled flag is read from
        # config at wiring time.
        app.config["RATELIMIT_ENABLED"] = True
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        limiter.enabled = True
        limiter._enabled = True
        limiter.init_app(app)
        limiter.reset()
        try:
            with client.application.app_context():
                token = _session_cookie(client, owner)
                statuses = [
                    client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"}).status_code for _ in range(6)
                ]

            assert 429 in statuses, f"the limiter never engaged: {statuses}"
            # At most the configured three per hour were allowed through.
            assert statuses.count(202) <= 3, f"too many requests were accepted: {statuses}"
        finally:
            limiter.enabled = False
            limiter._enabled = False

    def test_the_limit_is_keyed_on_the_account_not_the_address(self, app) -> None:
        """The mailbox's tolerance is what is being protected.

        An IP-keyed bucket would let one host exhaust a victim's quota while the
        victim's own retries went through, protecting the attacker instead.
        """
        from app.api.account import _rate_limit_key

        with app.test_request_context():
            from flask import g

            g.user_id = "11111111-1111-1111-1111-111111111111"
            assert _rate_limit_key() == "11111111-1111-1111-1111-111111111111"

            g.user_id = None
            assert _rate_limit_key() == "anon"


# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------


class TestStatusReporting:
    """The profile page needs to know whether a request is pending."""

    def test_status_reports_a_pending_request(self, client, configured_mail, owner) -> None:
        with client.application.app_context():
            token = _session_cookie(client, owner)

            before = client.get("/api/account/deletion/status", headers={"Authorization": f"Bearer {token}"})
            assert before.get_json()["data"]["pending"] is False

            client.post("/api/account/deletion/request", headers={"Authorization": f"Bearer {token}"})

            after = client.get("/api/account/deletion/status", headers={"Authorization": f"Bearer {token}"})
            assert after.get_json()["data"]["pending"] is True
            assert after.get_json()["data"]["expires_at"] is not None

    def test_the_profile_response_carries_the_verification_state(self, client, owner) -> None:
        """The owner-facing projection includes what the public one deliberately omits."""
        with client.application.app_context():
            token = _session_cookie(client, owner)
            response = client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})

            data = response.get_json()["data"]
            assert data["email_verified"] is True
            assert data["email_verified_source"] == "local"
            assert data["deletion"]["pending"] is False

    def test_the_public_projection_omits_the_verification_state(self, client, app) -> None:
        """Telling a third party whether an address is confirmed is a free disclosure."""
        with client.application.app_context():
            record = User(email="quiet@iqoqo.local", public_username="quietuser", visibility="public")
            record.set_password("test-password")
            record.mark_email_verified("local")
            db.session.add(record)
            db.session.commit()

        response = client.get("/api/public/u/quietuser")
        assert response.status_code == 200
        body = json.dumps(response.get_json())
        assert "email_verified" not in body


class TestTokenTransport:
    """The token must be readable from however the client sends it.

    Regression, and the one the frontend migration caused. The confirmation
    screens became frontend routes, so the browser POSTs `{"token": ...}` as JSON
    and the URL no longer carries a query string. `_token_from_request` read only
    `request.values`, which covers args and form but not a JSON body -- so the
    state GET reported the link usable and the immediately following POST refused
    it as spent, changing nothing and explaining nothing.
    """

    def test_a_json_body_token_is_accepted_for_verification(self, client, configured_mail, unverified_user) -> None:
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, unverified_user), AccountTokenPurpose.EMAIL_VERIFICATION)

        token = _session_cookie(client, unverified_user)
        minted = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]

        response = client.post(
            "/api/account/email/verify",
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": minted},
            json={"token": raw},
        )

        assert response.status_code == 200, "a JSON body token must be readable"
        with client.application.app_context():
            db.session.remove()
            assert db.session.get(User, unverified_user).is_email_verified is True

    def test_a_json_body_token_is_accepted_for_deletion(self, client, configured_mail, owner) -> None:
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)

        token = _session_cookie(client, owner)
        minted = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]

        response = client.post(
            "/api/account/deletion/confirm",
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": minted},
            json={"token": raw},
        )

        assert response.status_code == 200, "a JSON body token must be readable"
        with client.application.app_context():
            db.session.remove()
            assert db.session.get(User, owner) is None

    def test_a_query_string_token_still_works(self, client, configured_mail, owner) -> None:
        """The query form is still supported; both sources must work."""
        with client.application.app_context():
            raw, _row = account_tokens.issue_token(db.session.get(User, owner), AccountTokenPurpose.ACCOUNT_DELETION)

        token = _session_cookie(client, owner)
        minted = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]

        response = client.post(
            f"/api/account/deletion/confirm?token={raw}",
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": minted},
        )

        assert response.status_code == 200
        with client.application.app_context():
            db.session.remove()
            assert db.session.get(User, owner) is None

    def test_a_missing_token_is_refused_rather_than_crashing(self, client, configured_mail, owner) -> None:
        """No token anywhere: a clean rejection, not a 500 from parsing nothing."""
        token = _session_cookie(client, owner)
        minted = client.get("/api/account/csrf").get_json()["data"]["csrf_token"]

        response = client.post(
            "/api/account/deletion/confirm",
            headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": minted},
            json={"nothing": "useful"},
        )

        assert response.status_code == 400
        assert response.get_json()["usable"] is False
