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
"""Persist email-verification state and account-lifecycle tokens.

Two additions, both load-bearing for the account-deletion confirmation flow.

**``users.email_verified_at`` / ``users.email_verified_source``**

An address stored on a user row is not evidence of mailbox control.  It may
have been typed by whoever registered, inserted by an administrator, or copied
from an unverified federated claim.  The deletion confirmation flow gates on
proof of control, so that proof needs a column.

Both columns are added **nullable with no default**, which makes every
pre-existing row unverified.  That is the only safe direction: a migration
cannot retroactively establish who controlled a mailbox, and backfilling
``verified`` would re-enable irreversible account deletion for every existing
account on the strength of nothing.  Users re-confirm from the profile page; the
cost is one email, the alternative is a permanent authorisation to delete.

**``auth.account_action_tokens``**

One-use, purpose-bound, expiring credentials for the two actions that need a
second channel: verifying an address and confirming account deletion.  Only a
keyed digest is stored.

The partial unique index ``ix_auth_account_action_tokens_one_outstanding`` is
the load-bearing part.  It constrains ``(user_id, purpose)`` *among rows that
have not been consumed*, so a resend can only succeed by first retiring the
previous token.  Expressing that in the schema rather than in a
"delete then insert" code path means a resend still supersedes under two
concurrent requests, and a future caller that forgets to invalidate gets an
``IntegrityError`` rather than two live tokens.

``consumed_at IS NULL`` is written out separately per dialect rather than using
a shared ``sqlite_where``/``postgresql_where`` pair, because the two dialects
require different parameter styles and silently disagreeing on a partial-index
predicate is the same class of bug as the schema-qualified-name bug that
``v0_8_2_fk_index_names`` exists to undo.

Revision ID: v0_8_3_account_lifecycle
Revises: v0_8_2_fk_index_names
Create Date: 2026-10-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "v0_8_3_account_lifecycle"
down_revision = "v0_8_2_fk_index_names"
branch_labels = None
depends_on = None

#: Unqualified table name.  Every ``op.*`` call takes this and passes ``schema``
#: separately: handing Alembic a pre-qualified ``"auth.account_action_tokens"``
#: makes SQLAlchemy render it as ONE quoted identifier, which PostgreSQL then
#: looks for in ``search_path`` rather than in the ``auth`` schema.  See
#: ``v0_8_2_duplicate_provenance`` for the original form of this note.
_TOKEN_TABLE = "account_action_tokens"

#: Column types differ by dialect for the UUID and the token digest.  The digest
#: is always 64 lowercase hex characters, so ``String(64)`` is exact on both.
_USER_ID_TYPE_PG = postgresql.UUID(as_uuid=True)
_USER_ID_TYPE_SQLITE = sa.String(36)


def _is_pg() -> bool:
    """Whether the bound dialect names schemas."""
    return op.get_bind().dialect.name == "postgresql"


def _auth() -> str | None:
    """Return the auth schema name, or None on dialects without one."""
    return "auth" if _is_pg() else None


def _user_id_type() -> sa.types.TypeEngine:
    """Return the dialect-appropriate UUID column type."""
    return _USER_ID_TYPE_PG if _is_pg() else _USER_ID_TYPE_SQLITE


def _qualified_users(schema: str | None) -> str:
    """Return the reference target for the users foreign key.

    ``ForeignKeyConstraint`` needs the fully qualified name because it is
    rendered into the ``REFERENCES`` clause rather than resolved against the
    table's own schema.

    Args:
        schema: The auth schema name, or None on dialects without one.

    Returns:
        The reference target, always as ``<schema>.users`` or bare ``users``.
    """
    return "users" if schema is None else f"{schema}.users"


def upgrade():
    """Add the verification columns and the token table."""
    auth = _auth()

    # Nullable, no default: existing rows must come out unverified.  See the
    # module docstring for why backfilling is not merely inconvenient.
    with op.batch_alter_table("users", schema=auth) as batch_op:
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("email_verified_source", sa.String(length=16), nullable=True))

    op.create_table(
        _TOKEN_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", _user_id_type(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        # The purpose vocabulary is a CHECK rather than a Postgres enum so that
        # adding a purpose is a constraint change, not an enum type migration
        # that SQLite cannot express at all.
        sa.CheckConstraint(
            "purpose IN ('email_verification', 'account_deletion')",
            name="check_account_action_token_purpose",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{_qualified_users(auth)}.id"],
            ondelete="CASCADE",
        ),
        schema=auth,
    )

    # Lookup by digest is the only read path that matters on the hot route, and
    # it is a point lookup that must not degrade into a scan.
    op.create_index(
        "ix_auth_account_action_tokens_token_digest",
        _TOKEN_TABLE,
        ["token_digest"],
        unique=True,
        schema=auth,
    )

    # Cleanup sweeps this by expiry; without the index a purge is a full scan
    # of a table whose rows are all short-lived and all unique.
    op.create_index(
        "ix_auth_account_action_tokens_expires_at",
        _TOKEN_TABLE,
        ["expires_at"],
        schema=auth,
    )

    # Deleting a user takes their tokens with it.  PostgreSQL will not cascade
    # without a supporting index on the child side, so it is created here
    # rather than left to the cascade to scan for.
    op.create_index(
        "ix_auth_account_action_tokens_user_id",
        _TOKEN_TABLE,
        ["user_id"],
        schema=auth,
    )

    # Supersession, enforced by the schema.  See the module docstring.
    op.create_index(
        "ix_auth_account_action_tokens_one_outstanding",
        _TOKEN_TABLE,
        ["user_id", "purpose"],
        unique=True,
        schema=auth,
        sqlite_where=sa.text("consumed_at IS NULL"),
        postgresql_where=sa.text("consumed_at IS NULL"),
    )


def downgrade():
    """Drop the token table and the verification columns.

    Lossy by design: an outstanding deletion request loses its token, so a
    pending confirmation cannot be completed after a downgrade.  The account
    itself is untouched — deletion only ever happens on explicit confirmation —
    so this removes an ability, not data.  Consumed rows are dropped with the
    rest of the table; the audit they represent is not worth a migration that
    leaves a half-populated table behind.
    """
    auth = _auth()

    op.drop_index("ix_auth_account_action_tokens_one_outstanding", table_name=_TOKEN_TABLE, schema=auth)
    op.drop_index("ix_auth_account_action_tokens_user_id", table_name=_TOKEN_TABLE, schema=auth)
    op.drop_index("ix_auth_account_action_tokens_expires_at", table_name=_TOKEN_TABLE, schema=auth)
    op.drop_index("ix_auth_account_action_tokens_token_digest", table_name=_TOKEN_TABLE, schema=auth)
    op.drop_table(_TOKEN_TABLE, schema=auth)

    with op.batch_alter_table("users", schema=auth) as batch_op:
        batch_op.drop_column("email_verified_source")
        batch_op.drop_column("email_verified_at")


def _qualified_users(schema: str | None) -> str:
    """Return the schema-qualified users table name for a FK constraint.

    Unlike a ``op.*`` call, ``ForeignKeyConstraint`` needs the fully qualified
    target because it is rendered into the ``REFERENCES`` clause rather than
    looked up in the dialect's default search path.

    Args:
        schema: The auth schema name, or None on dialects without one.

    Returns:
        The reference target to embed in the constraint.
    """
    return "users" if schema is None else f"{schema}.users"
