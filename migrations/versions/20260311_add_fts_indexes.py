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
    # Add expression-based GIN indexes for fast Full-Text Search
    # using the 'simple' dictionary to gracefully handle ISBNs and mixed languages.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_works_fts ON works
        USING GIN (
            (to_tsvector('simple', coalesce(title, '')) ||
             to_tsvector('simple', coalesce((meta->>'authors'), '')))
        );
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_manifestations_fts ON manifestations
        USING GIN (
            to_tsvector('simple', coalesce(isbn13, ''))
        );
    """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_works_fts;")
    op.execute("DROP INDEX IF EXISTS ix_manifestations_fts;")
