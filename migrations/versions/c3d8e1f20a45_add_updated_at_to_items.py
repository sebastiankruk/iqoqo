"""Add updated_at column to items table.

Adds a ``updated_at`` timestamp column that is initialised from ``added_at``
for every existing row so that ordering-by-recency works correctly for
pre-migration data.  New rows have ``updated_at`` managed by SQLAlchemy's
``onupdate`` hook and default to the same instant as ``added_at``.

Revision ID: c3d8e1f20a45
Revises: f53e05847e86
Create Date: 2026-02-25 00:00:00.000000

"""

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

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d8e1f20a45"
down_revision = "f53e05847e86"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at to items and backfill from added_at."""
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # Backfill: for every existing row set updated_at = added_at so that
    # the COALESCE(updated_at, added_at) ordering expression works correctly
    # even before the first real update.
    op.execute("UPDATE items SET updated_at = added_at WHERE updated_at IS NULL")


def downgrade() -> None:
    """Remove updated_at from items."""
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
