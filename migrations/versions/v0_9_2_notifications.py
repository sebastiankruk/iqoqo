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
"""Create notifications table in social schema.

Revision ID: v0_9_2_notifications
Revises: v0_9_1_followers_unique
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "v0_9_2_notifications"
down_revision = "v0_9_1_followers_unique"
branch_labels = None
depends_on = None


def upgrade():
    """Create social.notifications table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    social_schema = "social" if is_pg else None
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)
    auth_users_fk = "auth.users.id" if is_pg else "users.id"

    if is_pg:
        op.execute("CREATE SCHEMA IF NOT EXISTS social")

    idx_prefix = "ix_social_notifications_" if is_pg else "ix_notifications_"

    if not inspector.has_table("notifications", schema=social_schema):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("user_id", uuid_type, sa.ForeignKey(auth_users_fk, ondelete="CASCADE"), nullable=False),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column("actor_uri", sa.String(500), nullable=True),
            sa.Column("target_iri", sa.String(500), nullable=True),
            sa.Column("payload_json", json_type, nullable=False, server_default=sa.text("'{}'::jsonb" if is_pg else "'{}'")),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            schema=social_schema,
        )
        with op.batch_alter_table("notifications", schema=social_schema) as batch_op:
            batch_op.create_index(f"{idx_prefix}user_id", ["user_id"])
            batch_op.create_index(f"{idx_prefix}type", ["type"])
            batch_op.create_index(f"{idx_prefix}created_at", ["created_at"])
            batch_op.create_index(f"{idx_prefix}user_unread", ["user_id", "read_at"])


def downgrade():
    """Drop notifications table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    social_schema = "social" if is_pg else None

    if inspector.has_table("notifications", schema=social_schema):
        op.drop_table("notifications", schema=social_schema)
