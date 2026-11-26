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
"""Add physical_location column and index to inventory.items.

Revision ID: v1_2_0_item_physical_location
Revises: v1_1_2_cross_media_work_links
Create Date: 2026-11-26 20:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "v1_2_0_item_physical_location"
down_revision = "v1_1_2_cross_media_work_links"
branch_labels = None
depends_on = None


def _inventory_schema() -> str | None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return "inventory"
    return None


def upgrade() -> None:
    """Add physical_location column and index on inventory.items."""
    schema = _inventory_schema()
    op.add_column(
        "items",
        sa.Column("physical_location", sa.String(length=255), nullable=True),
        schema=schema,
    )
    op.create_index(
        "ix_items_physical_location",
        "items",
        ["physical_location"],
        unique=False,
        schema=schema,
    )


def downgrade() -> None:
    """Drop physical_location index and column from inventory.items."""
    schema = _inventory_schema()
    op.drop_index("ix_items_physical_location", table_name="items", schema=schema)
    op.drop_column("items", "physical_location", schema=schema)
