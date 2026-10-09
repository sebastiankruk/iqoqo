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
"""Add from_owner_id and to_owner_id to item_custody_events.

Revision ID: v0_8_3_item_custody_owners
Revises: v0_8_3_semantic_links_status
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_3_item_custody_owners"
down_revision = "v0_8_3_semantic_links_status"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_inv = "inventory" if is_pg else None
    s_auth_pfx = "auth." if is_pg else ""

    op.add_column(
        "item_custody_events",
        sa.Column("from_owner_id", sa.UUID(), nullable=True),
        schema=s_inv,
    )
    op.add_column(
        "item_custody_events",
        sa.Column("to_owner_id", sa.UUID(), nullable=True),
        schema=s_inv,
    )

    if is_pg:
        op.create_foreign_key(
            "fk_item_custody_events_from_owner_id",
            "item_custody_events",
            "users",
            ["from_owner_id"],
            ["id"],
            source_schema=s_inv,
            referent_schema="auth",
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_item_custody_events_to_owner_id",
            "item_custody_events",
            "users",
            ["to_owner_id"],
            ["id"],
            source_schema=s_inv,
            referent_schema="auth",
            ondelete="SET NULL",
        )
    else:
        op.create_foreign_key(
            "fk_item_custody_events_from_owner_id",
            "item_custody_events",
            "users",
            ["from_owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_item_custody_events_to_owner_id",
            "item_custody_events",
            "users",
            ["to_owner_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_item_custody_events_from_owner_id",
        "item_custody_events",
        ["from_owner_id"],
        unique=False,
        schema=s_inv,
    )
    op.create_index(
        "ix_item_custody_events_to_owner_id",
        "item_custody_events",
        ["to_owner_id"],
        unique=False,
        schema=s_inv,
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_inv = "inventory" if is_pg else None

    op.drop_index("ix_item_custody_events_to_owner_id", table_name="item_custody_events", schema=s_inv)
    op.drop_index("ix_item_custody_events_from_owner_id", table_name="item_custody_events", schema=s_inv)
    op.drop_constraint("fk_item_custody_events_to_owner_id", "item_custody_events", type_="foreignkey", schema=s_inv)
    op.drop_constraint("fk_item_custody_events_from_owner_id", "item_custody_events", type_="foreignkey", schema=s_inv)
    op.drop_column("item_custody_events", "to_owner_id", schema=s_inv)
    op.drop_column("item_custody_events", "from_owner_id", schema=s_inv)
