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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Update FTS columns to use unaccent for diacritic-insensitive search

Revision ID: v0_8_4_fts_unaccent
Revises: v0_8_4_work_series_memberships
Create Date: 2026-01-12

Updates the full-text search computed columns on works and manifestations tables
to use immutable_unaccent() for diacritic-insensitive matching. This allows
queries like "milosc" to match "miłość" and "Garcia" to match "García".
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'v0_8_4_fts_unaccent'
down_revision = 'v0_8_4_work_series_memberships'
branch_labels = None
depends_on = None


def upgrade():
    """Update FTS columns to use unaccent for diacritic-insensitive search."""
    # Drop indexes first (required before dropping columns)
    op.execute("DROP INDEX IF EXISTS catalog.ix_works_fts")
    op.execute("DROP INDEX IF EXISTS catalog.ix_manifestations_fts")
    
    # Update works.fts_simple to use unaccent
    op.execute("ALTER TABLE catalog.works DROP COLUMN fts_simple")
    op.execute("""
        ALTER TABLE catalog.works
        ADD COLUMN fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector('simple'::regconfig, 
                immutable_unaccent(COALESCE(title, '')) || ' ' ||
                immutable_unaccent(COALESCE(meta->>'authors', ''))
            )
        ) STORED
    """)
    op.execute("CREATE INDEX ix_works_fts ON catalog.works USING gin(fts_simple)")

    # Update manifestations.fts_simple to use unaccent
    op.execute("ALTER TABLE catalog.manifestations DROP COLUMN fts_simple")
    op.execute("""
        ALTER TABLE catalog.manifestations
        ADD COLUMN fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector('simple'::regconfig,
                immutable_unaccent(COALESCE(isbn13, '')) || ' ' ||
                immutable_unaccent(COALESCE(meta->>'publisher', '')) || ' ' ||
                immutable_unaccent(COALESCE(meta->>'alt_title', ''))
            )
        ) STORED
    """)
    op.execute("CREATE INDEX ix_manifestations_fts ON catalog.manifestations USING gin(fts_simple)")


def downgrade():
    """Revert FTS columns to original definitions without unaccent."""
    # Drop indexes first (required before dropping columns)
    op.execute("DROP INDEX IF EXISTS catalog.ix_works_fts")
    op.execute("DROP INDEX IF EXISTS catalog.ix_manifestations_fts")
    
    # Revert works.fts_simple
    op.execute("ALTER TABLE catalog.works DROP COLUMN fts_simple")
    op.execute("""
        ALTER TABLE catalog.works
        ADD COLUMN fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector('simple'::regconfig,
                COALESCE(title, '') || ' ' ||
                COALESCE(meta->>'authors', '')
            )
        ) STORED
    """)
    op.execute("CREATE INDEX ix_works_fts ON catalog.works USING gin(fts_simple)")

    # Revert manifestations.fts_simple
    op.execute("ALTER TABLE catalog.manifestations DROP COLUMN fts_simple")
    op.execute("""
        ALTER TABLE catalog.manifestations
        ADD COLUMN fts_simple tsvector GENERATED ALWAYS AS (
            to_tsvector('simple'::regconfig,
                COALESCE(isbn13, '') || ' ' ||
                COALESCE(meta->>'publisher', '') || ' ' ||
                COALESCE(meta->>'alt_title', '')
            )
        ) STORED
    """)
    op.execute("CREATE INDEX ix_manifestations_fts ON catalog.manifestations USING gin(fts_simple)")
