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

"""Fix llm_telemetry sequence initialization

Revision ID: fix_llm_telemetry_sequence
Revises: 9ed9e764c2b0
Create Date: 2026-04-19 17:35:00.000000

PostgreSQL sequences need to be initialized with the current max ID to avoid
duplicate key violations when inserting new records.
This was missing from the original llm_telemetry table creation.
"""

from alembic import op
import sqlalchemy as sa


revision = "fix_llm_telemetry_sequence"
down_revision = "9ed9e764c2b0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        SELECT setval('inventory.llm_telemetry_id_seq', 
                   COALESCE((SELECT MAX(id) FROM inventory.llm_telemetry), 0))
    """)


def downgrade():
    pass
