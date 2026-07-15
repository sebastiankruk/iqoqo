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
"""add_idx_work_meta_genres_gin

Add a GIN index on the ``work.meta->'genres'`` JSONB path using
``jsonb_path_ops``.  This index accelerates the faceted-stats genre
aggregation queries and any ``@>`` containment checks on the genres field.

Revision ID: 3177c5e97570
Revises: 20260709_defer_tsvector
Create Date: 2026-07-14 22:09:57.829252

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "3177c5e97570"
down_revision = "20260709_defer_tsvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create GIN index on catalog.works meta->'genres' using jsonb_path_ops.

    The ``meta`` column is typed as JSON.  PostgreSQL GIN indexes with
    ``jsonb_path_ops`` require JSONB, so we create a *functional* index that
    casts the column inline: ``(meta::jsonb->'genres')``.
    """
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_work_meta_genres_gin "
        "ON catalog.works USING gin ((meta::jsonb->'genres') jsonb_path_ops)"
    )


def downgrade() -> None:
    """Drop GIN index on catalog.works meta->'genres'."""
    op.execute("DROP INDEX IF EXISTS catalog.idx_work_meta_genres_gin")
