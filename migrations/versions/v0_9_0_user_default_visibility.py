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
"""Add default_item_visibility to users.

Revision ID: v0_9_0_user_default_visibility
Revises: v0_9_0_federation_schema
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_9_0_user_default_visibility"
down_revision = "v0_9_0_federation_schema"
branch_labels = None
depends_on = None


def upgrade():
    """Add default_item_visibility column to users table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        columns = [col["name"] for col in inspector.get_columns("users", schema=auth_schema)]
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "default_item_visibility" not in columns:
                batch_op.add_column(
                    sa.Column("default_item_visibility", sa.String(20), nullable=False, server_default="private")
                )


def downgrade():
    """Remove default_item_visibility column from users table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    auth_schema = "auth" if is_pg else None

    if inspector.has_table("users", schema=auth_schema):
        columns = [col["name"] for col in inspector.get_columns("users", schema=auth_schema)]
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "default_item_visibility" in columns:
                batch_op.drop_column("default_item_visibility")
