"""add fts indexes

Revision ID: 20260311_fts
Revises: 2973a4475ace
Create Date: 2026-03-11 21:12:27.000000

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
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260311_fts"
down_revision = "2973a4475ace"
branch_labels = None
depends_on = None


def upgrade():
    # Add generated tsvector columns and GIN indexes for fast Full-Text Search
    # using the 'simple' dictionary to gracefully handle ISBNs and mixed languages.
    # The generated columns avoid expression-based indexes that are hard to
    # reuse consistently from API queries.
    op.execute(
        """
        ALTER TABLE works
        ADD COLUMN IF NOT EXISTS fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector(
                'simple',
                coalesce(title, '') || ' ' || coalesce(meta->>'authors', '')
            )
        ) STORED;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_works_fts
        ON works
        USING GIN (fts_simple);
        """
    )
    op.execute(
        """
        ALTER TABLE manifestations
        ADD COLUMN IF NOT EXISTS fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(isbn13, '') || ' ' || coalesce(meta->>'publisher', '') || ' ' || coalesce(meta->>'alt_title', ''))
        ) STORED;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_manifestations_fts
        ON manifestations
        USING GIN (fts_simple);
        """
    )


def downgrade():
    # Drop indexes first, then the generated columns.
    op.execute("DROP INDEX IF EXISTS ix_works_fts;")
    op.execute("DROP INDEX IF EXISTS ix_manifestations_fts;")
    op.execute(
        """
        ALTER TABLE works
        DROP COLUMN IF EXISTS fts_simple;
        """
    )
    op.execute(
        """
        ALTER TABLE manifestations
        DROP COLUMN IF EXISTS fts_simple;
        """
    )
