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
"""Allow friends_only in user visibility and default_item_visibility checks.

Revision ID: v0_9_4_user_friends_only_checks
Revises: v0_9_4_fed_trust_autoaccept
Create Date: 2026-10-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v0_9_4_user_friends_only_checks"
down_revision = "v0_9_4_fed_trust_autoaccept"
branch_labels = None
depends_on = None


def upgrade():
    """Update check_user_visibility and check_user_default_item_visibility constraints."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        user_checks = {check["name"] for check in inspector.get_check_constraints("users", schema=auth_schema)}
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            for ck in ("check_user_visibility", "ck_users_visibility"):
                if ck in user_checks:
                    batch_op.drop_constraint(ck, type_="check")
            batch_op.create_check_constraint(
                "check_user_visibility",
                "visibility IN ('private', 'friends_only', 'shared', 'public')",
            )

            if "check_user_default_item_visibility" in user_checks:
                batch_op.drop_constraint("check_user_default_item_visibility", type_="check")
            batch_op.create_check_constraint(
                "check_user_default_item_visibility",
                "default_item_visibility IN ('private', 'friends_only', 'shared', 'public')",
            )


def downgrade():
    """Revert user visibility check constraints to exclude friends_only."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        table_name = "auth.users" if is_pg else "users"
        bind.execute(sa.text(f"UPDATE {table_name} SET visibility = 'private' WHERE visibility = 'friends_only'"))
        bind.execute(
            sa.text(
                f"UPDATE {table_name} SET default_item_visibility = 'private' "
                f"WHERE default_item_visibility IN ('friends_only', 'shared')"
            )
        )
        user_checks = {check["name"] for check in inspector.get_check_constraints("users", schema=auth_schema)}
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "check_user_visibility" in user_checks:
                batch_op.drop_constraint("check_user_visibility", type_="check")
                batch_op.create_check_constraint(
                    "check_user_visibility",
                    "visibility IN ('private', 'shared', 'public')",
                )
            if "check_user_default_item_visibility" in user_checks:
                batch_op.drop_constraint("check_user_default_item_visibility", type_="check")
                batch_op.create_check_constraint(
                    "check_user_default_item_visibility",
                    "default_item_visibility IN ('private', 'public')",
                )
