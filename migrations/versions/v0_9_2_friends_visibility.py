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
"""Add Item.visibility, 3-tier user visibility constraints, and user_friendships table.

Revision ID: v0_9_2_friends_visibility
Revises: v0_9_2_notifications
Create Date: 2026-10-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v0_9_2_friends_visibility"
down_revision = "v0_9_2_notifications"
branch_labels = None
depends_on = None


def upgrade():
    """Apply 3-tier visibility extensions and user_friendships table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    auth_schema = "auth" if is_pg else None
    inventory_schema = "inventory" if is_pg else None
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)
    auth_users_fk = "auth.users.id" if is_pg else "users.id"

    # 1. Add visibility column to items table if not present
    items_cols = [c["name"] for c in inspector.get_columns("items", schema=inventory_schema)]
    if "visibility" not in items_cols:
        op.add_column(
            "items",
            sa.Column("visibility", sa.String(20), nullable=False, server_default="public"),
            schema=inventory_schema,
        )
        # Backfill visibility from is_hidden
        if is_pg:
            op.execute(
                f"UPDATE {inventory_schema}.items SET visibility = CASE WHEN is_hidden = TRUE THEN 'private' ELSE 'public' END"
            )
        else:
            op.execute("UPDATE items SET visibility = CASE WHEN is_hidden = 1 THEN 'private' ELSE 'public' END")

    # 2. Add user_friendships table if not present
    if not inspector.has_table("user_friendships", schema=auth_schema):
        op.create_table(
            "user_friendships",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("requester_id", uuid_type, sa.ForeignKey(auth_users_fk, ondelete="CASCADE"), nullable=False),
            sa.Column("addressee_id", uuid_type, sa.ForeignKey(auth_users_fk, ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("requester_id", "addressee_id", name="uq_user_friendships_pair"),
            schema=auth_schema,
        )
        op.create_index(
            "ix_user_friendships_requester",
            "user_friendships",
            ["requester_id"],
            schema=auth_schema,
        )
        op.create_index(
            "ix_user_friendships_addressee",
            "user_friendships",
            ["addressee_id"],
            schema=auth_schema,
        )


def downgrade():
    """Revert 3-tier visibility extensions and user_friendships table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    auth_schema = "auth" if is_pg else None
    inventory_schema = "inventory" if is_pg else None

    if inspector.has_table("user_friendships", schema=auth_schema):
        op.drop_table("user_friendships", schema=auth_schema)

    items_cols = [c["name"] for c in inspector.get_columns("items", schema=inventory_schema)]
    if "visibility" in items_cols:
        op.drop_column("items", "visibility", schema=inventory_schema)
