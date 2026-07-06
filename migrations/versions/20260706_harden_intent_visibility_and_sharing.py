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
"""Add UserWorkIntent.is_hidden and harden shared_collections tokens (v0.7.6 security pass).

Revision ID: 20260706_harden_intent_vis
Revises: 52b02a37b16b
Create Date: 2026-07-06 12:00:00.000000

- `user_work_intents.is_hidden`: mirrors `items.is_hidden` so wishlist entries can
  be shared with other authenticated users by default (e.g. gift ideas for
  friends/family), with an explicit per-entry opt-out.
- `shared_collections.share_token`: widened from String(36) (UUID4, 122 bits) to
  String(64) to fit `secrets.token_urlsafe(32)` (256 bits).
- `shared_collections.expires_at`: optional TTL for shared links.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260706_harden_intent_vis"
down_revision = "52b02a37b16b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    schema = "inventory" if bind.dialect.name == "postgresql" else None

    def has_column(table_name, column_name, schema=None):
        columns = inspector.get_columns(table_name, schema=schema)
        return any(c["name"] == column_name for c in columns)

    if inspector.has_table("user_work_intents", schema=schema):
        if not has_column("user_work_intents", "is_hidden", schema):
            op.add_column(
                "user_work_intents",
                sa.Column("is_hidden", sa.Boolean(), server_default="false", nullable=False),
                schema=schema,
            )

    if inspector.has_table("shared_collections", schema=schema):
        if not has_column("shared_collections", "expires_at", schema):
            op.add_column(
                "shared_collections",
                sa.Column("expires_at", sa.DateTime(), nullable=True),
                schema=schema,
            )
        # Widen share_token to fit secrets.token_urlsafe(32) (43 chars, was UUID4/36).
        with op.batch_alter_table("shared_collections", schema=schema) as batch_op:
            batch_op.alter_column(
                "share_token",
                existing_type=sa.String(length=36),
                type_=sa.String(length=64),
                existing_nullable=False,
            )


def downgrade():
    bind = op.get_bind()
    schema = "inventory" if bind.dialect.name == "postgresql" else None

    with op.batch_alter_table("shared_collections", schema=schema) as batch_op:
        batch_op.alter_column(
            "share_token",
            existing_type=sa.String(length=64),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
    op.drop_column("shared_collections", "expires_at", schema=schema)
    op.drop_column("user_work_intents", "is_hidden", schema=schema)
