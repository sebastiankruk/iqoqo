"""Add updated_at column to items table.

Adds a ``updated_at`` timestamp column that is initialised from ``added_at``
for every existing row so that ordering-by-recency works correctly for
pre-migration data.  New rows have ``updated_at`` managed by SQLAlchemy's
``onupdate`` hook and default to the same instant as ``added_at``.

Revision ID: c3d8e1f20a45
Revises: f53e05847e86
Create Date: 2026-02-25 00:00:00.000000

"""

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
