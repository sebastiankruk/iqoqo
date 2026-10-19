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
"""Add composite unique constraint on federation_followers and check constraint on user default_item_visibility.

Revision ID: v0_9_1_followers_unique
Revises: v0_9_0_user_default_visibility
Create Date: 2026-10-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_9_1_followers_unique"
down_revision = "v0_9_0_user_default_visibility"
branch_labels = None
depends_on = None


def upgrade():
    """Apply check_user_default_item_visibility and uq_federation_followers_pair."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None
    fed_schema = "federation" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            batch_op.create_check_constraint(
                "check_user_default_item_visibility",
                "default_item_visibility IN ('private', 'public')",
            )

    if inspector.has_table("federation_followers", schema=fed_schema):
        with op.batch_alter_table("federation_followers", schema=fed_schema) as batch_op:
            batch_op.create_unique_constraint(
                "uq_federation_followers_pair",
                ["local_user_id", "remote_actor_id"],
            )


def downgrade():
    """Drop uq_federation_followers_pair and check_user_default_item_visibility."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None
    fed_schema = "federation" if is_pg else None

    if inspector.has_table("federation_followers", schema=fed_schema):
        with op.batch_alter_table("federation_followers", schema=fed_schema) as batch_op:
            batch_op.drop_constraint("uq_federation_followers_pair", type_="unique")

    if inspector.has_table("users", schema=auth_schema):
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            batch_op.drop_constraint("check_user_default_item_visibility", type_="check")
