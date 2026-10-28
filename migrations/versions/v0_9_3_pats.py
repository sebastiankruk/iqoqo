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
"""Add personal_access_tokens table and totp 2fa columns to users table.

Revision ID: v0_9_3_pats
Revises: v0_9_2_friends_visibility
Create Date: 2026-10-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v0_9_3_pats"
down_revision = "v0_9_2_friends_visibility"
branch_labels = None
depends_on = None


def upgrade():
    """Apply personal_access_tokens table and totp columns."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    auth_schema = "auth" if is_pg else None
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)
    auth_users_fk = "auth.users.id" if is_pg else "users.id"

    # 1. Add TOTP columns to users table if not present
    users_cols = [c["name"] for c in inspector.get_columns("users", schema=auth_schema)]
    if "totp_enabled" not in users_cols:
        op.add_column(
            "users",
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema=auth_schema,
        )
    if "totp_secret" not in users_cols:
        op.add_column(
            "users",
            sa.Column("totp_secret", sa.Text(), nullable=True),
            schema=auth_schema,
        )
    if "totp_recovery_codes" not in users_cols:
        op.add_column(
            "users",
            sa.Column("totp_recovery_codes", sa.JSON(), nullable=True),
            schema=auth_schema,
        )

    # 2. Add personal_access_tokens table if not present
    if not inspector.has_table("personal_access_tokens", schema=auth_schema):
        op.create_table(
            "personal_access_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", uuid_type, sa.ForeignKey(auth_users_fk, ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("token_prefix", sa.String(16), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            schema=auth_schema,
        )
        op.create_index(
            "ix_auth_personal_access_tokens_user_id" if is_pg else "ix_personal_access_tokens_user_id",
            "personal_access_tokens",
            ["user_id"],
            unique=False,
            schema=auth_schema,
        )
        op.create_index(
            "ix_auth_personal_access_tokens_token_prefix" if is_pg else "ix_personal_access_tokens_token_prefix",
            "personal_access_tokens",
            ["token_prefix"],
            unique=False,
            schema=auth_schema,
        )
        op.create_index(
            "ix_auth_personal_access_tokens_token_hash" if is_pg else "ix_personal_access_tokens_token_hash",
            "personal_access_tokens",
            ["token_hash"],
            unique=True,
            schema=auth_schema,
        )


def downgrade():
    """Revert personal_access_tokens table and totp columns."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    auth_schema = "auth" if is_pg else None

    if inspector.has_table("personal_access_tokens", schema=auth_schema):
        op.drop_index(
            "ix_auth_personal_access_tokens_token_hash" if is_pg else "ix_personal_access_tokens_token_hash",
            table_name="personal_access_tokens",
            schema=auth_schema,
        )
        op.drop_index(
            "ix_auth_personal_access_tokens_token_prefix" if is_pg else "ix_personal_access_tokens_token_prefix",
            table_name="personal_access_tokens",
            schema=auth_schema,
        )
        op.drop_index(
            "ix_auth_personal_access_tokens_user_id" if is_pg else "ix_personal_access_tokens_user_id",
            table_name="personal_access_tokens",
            schema=auth_schema,
        )
        op.drop_table("personal_access_tokens", schema=auth_schema)

    users_cols = [c["name"] for c in inspector.get_columns("users", schema=auth_schema)]
    if "totp_recovery_codes" in users_cols:
        op.drop_column("users", "totp_recovery_codes", schema=auth_schema)
    if "totp_secret" in users_cols:
        op.drop_column("users", "totp_secret", schema=auth_schema)
    if "totp_enabled" in users_cols:
        op.drop_column("users", "totp_enabled", schema=auth_schema)
