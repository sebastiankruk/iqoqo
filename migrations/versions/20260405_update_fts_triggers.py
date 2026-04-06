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
"""Add FTS triggers for video and board games

Revision ID: 20260405_fts_video_games
Revises: 08ac7a22bd8c
Create Date: 2026-04-05 22:00:00.000000

Adds Full-Text Search (FTS) support for video and board games by:

- Adding a ``search_vector`` tsvector column to ``catalog.works``
- Creating a trigger function to automatically update the vector with
  Cast names, Directors, and Board Game mechanics from the JSON ``meta``
  field
- Creating a GIN index for efficient full-text search queries

"""
from alembic import op

revision = "20260405_fts_video_games"
down_revision = "08ac7a22bd8c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE catalog.works ADD COLUMN IF NOT EXISTS search_vector tsvector;"
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION catalog.update_video_game_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('simple',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.meta->>'authors', '') || ' ' ||
                coalesce(NEW.meta->>'author', '') || ' ' ||
                coalesce(NEW.meta->>'directors', '') || ' ' ||
                coalesce(NEW.meta->>'Director', '') || ' ' ||
                coalesce(NEW.meta->>'cast', '') || ' ' ||
                coalesce(NEW.meta->>'Cast', '') || ' ' ||
                coalesce(NEW.meta->>'mechanics', '') || ' ' ||
                coalesce(NEW.meta->>'Mechanics', '') || ' ' ||
                coalesce(NEW.meta->>'game_mechanics', '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_update_video_game_search_vector ON catalog.works;
        CREATE TRIGGER trg_update_video_game_search_vector
        BEFORE INSERT OR UPDATE ON catalog.works
        FOR EACH ROW EXECUTE FUNCTION catalog.update_video_game_search_vector();
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_works_search_vector ON catalog.works USING GIN (search_vector);"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_works_search_vector;")
    op.execute("DROP TRIGGER IF EXISTS trg_update_video_game_search_vector ON catalog.works;")
    op.execute("DROP FUNCTION IF EXISTS catalog.update_video_game_search_vector();")
    op.execute("ALTER TABLE catalog.works DROP COLUMN IF EXISTS search_vector;")
