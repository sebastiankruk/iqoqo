"""rename_expression_content_types

Revision ID: 51a5cbb508f8
Revises: fix_llm_telemetry_sequence
Create Date: 2026-04-21 21:30:59.009915

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
revision = "51a5cbb508f8"
down_revision = "fix_llm_telemetry_sequence"
branch_labels = None
depends_on = None


def upgrade():
    # Mappings: sound -> music, moving image -> movie, boardgame -> board_game, three-dimensional object -> puzzle
    op.execute("UPDATE catalog.expressions SET content_type = 'music' WHERE content_type = 'sound'")
    op.execute("UPDATE catalog.expressions SET content_type = 'movie' WHERE content_type = 'moving image'")
    op.execute("UPDATE catalog.expressions SET content_type = 'board_game' WHERE content_type = 'boardgame'")
    op.execute("UPDATE catalog.expressions SET content_type = 'puzzle' WHERE content_type = 'three-dimensional object'")
    # Fallback for SQLite (no schema)
    op.execute("UPDATE expressions SET content_type = 'music' WHERE content_type = 'sound'")
    op.execute("UPDATE expressions SET content_type = 'movie' WHERE content_type = 'moving image'")
    op.execute("UPDATE expressions SET content_type = 'board_game' WHERE content_type = 'boardgame'")
    op.execute("UPDATE expressions SET content_type = 'puzzle' WHERE content_type = 'three-dimensional object'")


def downgrade():
    op.execute("UPDATE catalog.expressions SET content_type = 'sound' WHERE content_type = 'music'")
    op.execute("UPDATE catalog.expressions SET content_type = 'moving image' WHERE content_type = 'movie'")
    op.execute("UPDATE catalog.expressions SET content_type = 'boardgame' WHERE content_type = 'board_game'")
    op.execute("UPDATE catalog.expressions SET content_type = 'three-dimensional object' WHERE content_type = 'puzzle'")
    # Fallback for SQLite
    op.execute("UPDATE expressions SET content_type = 'sound' WHERE content_type = 'music'")
    op.execute("UPDATE expressions SET content_type = 'moving image' WHERE content_type = 'movie'")
    op.execute("UPDATE expressions SET content_type = 'boardgame' WHERE content_type = 'board_game'")
    op.execute("UPDATE expressions SET content_type = 'three-dimensional object' WHERE content_type = 'puzzle'")
