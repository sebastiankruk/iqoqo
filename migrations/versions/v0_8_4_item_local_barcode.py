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
"""Add local_barcode column to items table.

Supports exemplar-level physical inventory asset tagging and circulation tracking.

Revision ID: v0_8_4_item_local_barcode
Revises: v0_8_4_fts_unaccent
Create Date: 2026-10-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_8_4_item_local_barcode"
down_revision = "v0_8_4_fts_unaccent"
branch_labels = None
depends_on = None


def upgrade():
    """Add local_barcode column and index to items table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inventory = "inventory" if is_pg else None
    idx_name = "ix_inventory_items_local_barcode" if is_pg else "ix_items_local_barcode"

    with op.batch_alter_table("items", schema=inventory) as batch_op:
        batch_op.add_column(sa.Column("local_barcode", sa.String(64), nullable=True))
        batch_op.create_index(idx_name, ["local_barcode"], unique=False)


def downgrade():
    """Drop local_barcode index and column from items table."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inventory = "inventory" if is_pg else None
    idx_name = "ix_inventory_items_local_barcode" if is_pg else "ix_items_local_barcode"

    with op.batch_alter_table("items", schema=inventory) as batch_op:
        batch_op.drop_index(idx_name)
        batch_op.drop_column("local_barcode")
