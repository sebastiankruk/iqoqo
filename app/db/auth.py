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
"""Authentication and RBAC models (public schema)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship
from werkzeug.security import check_password_hash, generate_password_hash

if TYPE_CHECKING:
    from app.core.permissions import PermissionName

from . import db

# ---------------------------------------------------------------------------
# Schema selector
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

_AUTH: str | None = "auth" if _USE_PG else None
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""

# ---------------------------------------------------------------------------
# RBAC association tables
# ---------------------------------------------------------------------------

user_roles = db.Table(
    "user_roles",
    db.metadata,
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}roles.id", ondelete="CASCADE"), primary_key=True),
    schema=_AUTH,
)

role_permissions = db.Table(
    "role_permissions",
    db.metadata,
    db.Column("role_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}permissions.id", ondelete="CASCADE"), primary_key=True),
    schema=_AUTH,
)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TokenBlocklist(db.Model):  # type: ignore[name-defined]
    """JWT token revocation blocklist."""

    __tablename__ = "token_blocklist"
    __table_args__ = (
        (
            db.Index("ix_auth_token_blocklist_expires_at", "expires_at"),
            {"schema": _AUTH},
        )
        if _AUTH
        else (db.Index("ix_auth_token_blocklist_expires_at", "expires_at"),)
    )

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def prune_expired(cls) -> int:
        """Prune tokens where expires_at < now to reclaim database storage."""
        now = datetime.now(UTC)
        stmt = db.delete(cls).where(cls.expires_at.is_not(None), cls.expires_at < now)
        res = db.session.execute(stmt)
        db.session.commit()
        count = getattr(res, "rowcount", 0)
        return int(count) if count is not None else 0

    @classmethod
    def is_revoked(cls, jti: str | None) -> bool:
        """Check if a token jti is present in the blocklist using constant-time comparison."""
        if not jti:
            return False
        import hmac

        entry = db.session.execute(db.select(cls).filter_by(jti=jti)).scalar_one_or_none()
        if entry and entry.jti:
            return hmac.compare_digest(entry.jti, jti)
        return False


class OAuthExchangeCode(db.Model):  # type: ignore[name-defined]
    """Short-lived, single-use OAuth handoff code; only its SHA-256 digest is stored."""

    __tablename__ = "oauth_exchange_codes"
    __table_args__ = (
        db.Index("ix_auth_oauth_exchange_codes_expires_at" if _AUTH else "ix_oauth_exchange_codes_expires_at", "expires_at"),
        *(({"schema": _AUTH},) if _AUTH else ()),
    )

    code_hash = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    callback_url = db.Column(db.String(2048), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Account lifecycle
# ---------------------------------------------------------------------------


class AccountTokenPurpose(StrEnum):
    """The closed set of account-lifecycle actions a token may authorise.

    A token carries its purpose in the row it is persisted as *and* in the key
    used to derive its digest, so a token minted for one purpose can neither be
    replayed against the other endpoint nor be recognised there even if a caller
    submits it verbatim.  Adding a purpose here is a deliberate widening of what
    a single-use credential can authorise; the test suite asserts that every
    purpose has a matching column-length allowance and a consuming endpoint.
    """

    EMAIL_VERIFICATION = "email_verification"
    ACCOUNT_DELETION = "account_deletion"


#: Column width for :attr:`AccountActionToken.purpose`.  Sized to hold every
#: member of :class:`AccountTokenPurpose` with room to spare, and asserted
#: against the enum in the test suite so a longer member cannot be silently
#: truncated by PostgreSQL.
TOKEN_PURPOSE_LENGTH = 32


class AccountActionToken(db.Model):  # type: ignore[name-defined]
    """Single-use, purpose-bound, expiring credential for an account action.

    Only a keyed digest of the token is stored, never the token itself: a leaked
    database row — or a backup, or a log of the query that read it — therefore
    yields no usable credential.  The row additionally pins the account, the
    purpose, the address the token was issued for, and an expiry, so a token
    cannot be widened, retargeted at another mailbox, or replayed.

    At most one *outstanding* token may exist per ``(user_id, purpose)`` pair.
    That is enforced by a partial unique index rather than by application code,
    so a resend supersedes the previous token even when two requests race and
    even if a future caller forgets to invalidate first.
    """

    __tablename__ = "account_action_tokens"
    __table_args__ = (
        # Index names are declared explicitly rather than inferred from
        # `index=True`.  SQLAlchemy derives `ix_<schema>_<table>_<column>` only
        # when the table carries a schema, so a bare table silently produces a
        # different name on SQLite than on PostgreSQL -- the model/migration
        # divergence that `v0_8_2_fk_index_names` exists to undo.  Naming them
        # here makes the agreement dialect-independent.
        db.Index("ix_auth_account_action_tokens_token_digest", "token_digest", unique=True),
        db.Index("ix_auth_account_action_tokens_user_id", "user_id"),
        # Supersession: a resend may only ever insert after the previous
        # outstanding token for the same account and purpose has been consumed
        # or deleted.  `consumed_at IS NULL` is the "outstanding" predicate, and
        # a partial unique index is the only form of that constraint both
        # PostgreSQL and SQLite support.
        db.Index(
            "ix_auth_account_action_tokens_one_outstanding",
            "user_id",
            "purpose",
            unique=True,
            sqlite_where=db.text("consumed_at IS NULL"),
            postgresql_where=db.text("consumed_at IS NULL"),
        ),
        # Cleanup sweeps this by expiry; without the index a purge is a full
        # scan of a table whose rows are all short-lived.
        db.Index(
            "ix_auth_account_action_tokens_expires_at",
            "expires_at",
        ),
        db.CheckConstraint(
            f"purpose IN ('{AccountTokenPurpose.EMAIL_VERIFICATION.value}', '{AccountTokenPurpose.ACCOUNT_DELETION.value}')",
            name="check_account_action_token_purpose",
        ),
        *(({"schema": _AUTH},) if _AUTH else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose = db.Column(String(TOKEN_PURPOSE_LENGTH), nullable=False)
    #: Keyed digest (hex, 64 chars) of the raw token.  Unique so a collision --
    #: which a 256-bit token makes negligible -- fails loudly instead of
    #: resolving to whichever row the query happened to find first.
    token_digest = db.Column(String(64), nullable=False)
    #: The address the token was issued for, copied at issue time.  A
    #: verification token is only honoured while this still matches the
    #: account's current address, so changing the address invalidates it even if
    #: the row somehow survives.
    email = db.Column(String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @property
    def is_outstanding(self) -> bool:
        """Whether this token may still be presented.

        Read-side only.  Acceptance still re-checks under a row lock in
        :mod:`app.core.account_tokens`; a property here exists for the API
        surfaces that only report state.
        """
        if self.consumed_at is not None:
            return False
        return _as_utc(self.expires_at) > datetime.now(UTC)

    @classmethod
    def purge_expired(cls, now: datetime | None = None) -> int:
        """Delete rows whose expiry has passed and return how many went away.

        Consumed rows are retained until they expire: an audit trail that a
        token *was* used is worth more than the bytes, and the rows are bounded
        by the token expiry rather than by usage.

        Args:
            now: Override for the current time; used by tests to exercise the
                boundary without sleeping.

        Returns:
            The number of rows deleted.
        """
        from . import db as _db

        cutoff = now or datetime.now(UTC)
        # SQLite stores `DateTime` values without a timezone, so comparing a
        # column read back as naive against an aware `now()` raises rather than
        # working. Binding a naive cutoff there keeps both dialects on the same
        # code path; PostgreSQL compares an aware value to an aware column and
        # is unaffected by the bound parameter's shape.
        if _db.session.get_bind().dialect.name == "sqlite":
            cutoff = cutoff.replace(tzinfo=None)
        result = _db.session.execute(_db.delete(cls).where(cls.expires_at <= cutoff))
        return int(getattr(result, "rowcount", 0) or 0)


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalise a stored timestamp to timezone-aware UTC.

    SQLite round-trips ``DateTime(timezone=True)`` as a naive value, so a token
    read back from the test database would otherwise be compared against an
    aware ``now()`` and raise.  Production PostgreSQL is already aware, so this
    is a no-op there.

    Args:
        value: The stored timestamp, or None.

    Returns:
        An aware UTC datetime, or None when ``value`` was None.
    """
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class Permission(db.Model):  # type: ignore[name-defined]
    """A granular permission that can be assigned to roles."""

    __tablename__ = "permissions"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))


class Role(db.Model):  # type: ignore[name-defined]
    """A named role that aggregates permissions."""

    __tablename__ = "roles"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    permissions: Mapped[list[Permission]] = relationship("Permission", secondary=role_permissions, lazy="selectin")


class User(db.Model):  # type: ignore[name-defined]
    """
    Application user.  Supports local password auth as well as Google OAuth.
    """

    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint("visibility IN ('private', 'shared', 'public')", name="check_user_visibility"),
        db.CheckConstraint("password_hash IS NOT NULL OR google_id IS NOT NULL", name="check_user_auth_method"),
        *(({"schema": _AUTH},) if _AUTH else ()),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(100))
    public_username = db.Column(db.String(50), unique=True, nullable=True, index=True)
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_login = db.Column(db.DateTime, nullable=True)
    visibility = db.Column(db.String(20), default="private")

    # -- Email verification -------------------------------------------------
    # The address on the row is *not* evidence of mailbox control: it may have
    # been supplied by whoever registered, typed by an administrator, or copied
    # from an unverified federated claim.  These two columns are the only
    # trustworthy signal, and account deletion is gated on them.
    #
    # Both start NULL, including for rows that predate this column.  A migration
    # cannot retroactively prove control of a mailbox, and defaulting to
    # "verified" would silently re-enable deletion for every existing account
    # based on nothing.
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    #: Where the verification came from: ``local`` (a confirmation link the owner
    #: followed) or ``oidc`` (a validated identity response asserting
    #: `email_verified`).  Kept for audit and so a future policy can require
    #: re-verification of federated addresses without losing the history.
    email_verified_source = db.Column(db.String(16), nullable=True)

    roles: Mapped[list[Role]] = relationship("Role", secondary=user_roles, lazy="selectin", backref=db.backref("users", lazy="dynamic"))
    items = db.relationship("Item", foreign_keys="Item.owner_id", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    lent_items = db.relationship("Item", foreign_keys="Item.lent_to_user_id", backref="borrower", lazy="dynamic")
    consents = db.relationship("ConsentRecord", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_email_verified(self) -> bool:
        """Whether the address currently stored on the account is verified."""
        return self.email_verified_at is not None

    @property
    def has_verified_email(self) -> bool:
        """Whether the account owns a usable, verified address.

        Distinct from :attr:`is_email_verified` in intent only: both reduce to
        the same predicate today, but the API surfaces and the deletion gate read
        better as "does this account have an address it can be reached at".
        """
        return bool(self.email) and self.email_verified_at is not None

    def mark_email_verified(self, source: str) -> None:
        """Record mailbox control of the current address.

        Args:
            source: Where the evidence came from — ``local`` or ``oidc``.  The
                column is a ``String(16)``; the test suite asserts both accepted
                values fit.
        """
        if len(source) > 16:
            raise ValueError(f"email verification source {source!r} exceeds the 16-character column width")
        self.email_verified_at = datetime.now(UTC)
        self.email_verified_source = source

    def clear_email_verification(self) -> None:
        """Drop verification state, leaving the address itself untouched."""
        self.email_verified_at = None
        self.email_verified_source = None

    def set_password(self, password: str) -> None:
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if *password* matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: PermissionName | str) -> bool:
        """Return True if the user holds *permission_name* through any role."""
        perm_val = permission_name.value if hasattr(permission_name, "value") else permission_name
        for role in self.roles:  # type: ignore[attr-defined]
            for perm in role.permissions:  # type: ignore[attr-defined]
                if perm.name == perm_val:
                    return True
        return False

    def to_dict(self) -> dict:
        """Serialize core user fields for API responses and tests."""
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "display_name": self.display_name,
            "public_username": self.public_username,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_private_dict(self) -> dict:
        """Serialize fields only the account owner may read.

        Separated from :meth:`to_dict` because the verification state is
        deliberately *not* in the public projection: telling a third party
        whether an address is confirmed is a small but free disclosure, and the
        owner-facing surfaces are the only consumers that need it.
        """
        data = self.to_dict()
        data.update(
            {
                "email_verified": self.is_email_verified,
                "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
                "email_verified_source": self.email_verified_source,
            }
        )
        return data


    @classmethod
    def list_llm_permissions(cls, user: User | None) -> dict[str, bool]:
        """Return a dict of LLM-related permissions for *user*."""
        if not user:
            return {
                "allow_generate_cover": False,
                "allow_cloud_llm": False,
                "allow_generate_metadata": False,
            }

        from app.core.permissions import PermissionName

        return {
            "allow_generate_cover": user.has_permission(PermissionName.LLM_GENERATE_COVER),
            "allow_cloud_llm": user.has_permission(PermissionName.LLM_GENERATE_CLOUD),
            "allow_generate_metadata": user.has_permission(PermissionName.LLM_GENERATE_METADATA),
        }


class ConsentRecord(db.Model):  # type: ignore[name-defined]
    """GDPR consent record for a user."""

    __tablename__ = "user_consents"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False)
    consent_type = db.Column(db.String(50), nullable=False, index=True)
    is_granted = db.Column(db.Boolean, nullable=False)
    policy_version = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
