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
"""Add apple_id to users and update auth method check constraint.

Revision ID: v1_0_0_add_apple_id_to_users
Revises: v0_9_4_user_friends_only_checks
Create Date: 2026-11-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v1_0_0_add_apple_id_to_users"
down_revision = "v0_9_4_user_friends_only_checks"
branch_labels = None
depends_on = None


def upgrade():
    """Add apple_id column and update check_user_auth_method constraint."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        columns = {col["name"] for col in inspector.get_columns("users", schema=auth_schema)}
        user_checks = {check["name"] for check in inspector.get_check_constraints("users", schema=auth_schema)}

        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "apple_id" not in columns:
                batch_op.add_column(sa.Column("apple_id", sa.String(255), nullable=True))
                batch_op.create_index("ix_users_apple_id", ["apple_id"], unique=True)

            if "check_user_auth_method" in user_checks:
                batch_op.drop_constraint("check_user_auth_method", type_="check")
            batch_op.create_check_constraint(
                "check_user_auth_method",
                "password_hash IS NOT NULL OR google_id IS NOT NULL OR apple_id IS NOT NULL",
            )


def downgrade():
    """Revert apple_id column and check_user_auth_method constraint."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        columns = {col["name"] for col in inspector.get_columns("users", schema=auth_schema)}
        user_checks = {check["name"] for check in inspector.get_check_constraints("users", schema=auth_schema)}

        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "check_user_auth_method" in user_checks:
                batch_op.drop_constraint("check_user_auth_method", type_="check")
            batch_op.create_check_constraint(
                "check_user_auth_method",
                "password_hash IS NOT NULL OR google_id IS NOT NULL",
            )

            if "apple_id" in columns:
                batch_op.drop_index("ix_users_apple_id")
                batch_op.drop_column("apple_id")
