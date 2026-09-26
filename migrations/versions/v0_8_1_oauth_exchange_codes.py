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
"""Store hashed, expiring OAuth handoff codes for single-use exchange.

Revision ID: v0_8_1_oauth_exchange_codes
Revises: v0_8_1_security_constraints
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_1_oauth_exchange_codes"
down_revision = "v0_8_1_security_constraints"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    auth_schema = "auth" if is_pg else None
    auth_users_table = f"{auth_schema}.users" if auth_schema else "users"

    op.create_table(
        "oauth_exchange_codes",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("callback_url", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], [auth_users_table + ".id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("code_hash"),
        schema=auth_schema,
    )
    op.create_index(
        "ix_auth_oauth_exchange_codes_user_id" if is_pg else "ix_oauth_exchange_codes_user_id",
        "oauth_exchange_codes",
        ["user_id"],
        unique=False,
        schema=auth_schema,
    )
    op.create_index(
        "ix_auth_oauth_exchange_codes_expires_at" if is_pg else "ix_oauth_exchange_codes_expires_at",
        "oauth_exchange_codes",
        ["expires_at"],
        unique=False,
        schema=auth_schema,
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    auth_schema = "auth" if is_pg else None
    op.drop_index(
        "ix_auth_oauth_exchange_codes_expires_at" if is_pg else "ix_oauth_exchange_codes_expires_at",
        table_name="oauth_exchange_codes",
        schema=auth_schema,
    )
    op.drop_index(
        "ix_auth_oauth_exchange_codes_user_id" if is_pg else "ix_oauth_exchange_codes_user_id",
        table_name="oauth_exchange_codes",
        schema=auth_schema,
    )
    op.drop_table("oauth_exchange_codes", schema=auth_schema)
