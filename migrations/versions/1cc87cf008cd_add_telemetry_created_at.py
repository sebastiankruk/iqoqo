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
"""add telemetry created_at

Revision ID: 1cc87cf008cd
Revises: 47e29c185dbb
Create Date: 2026-04-03 15:46:13.302826

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1cc87cf008cd'
down_revision = '47e29c185dbb'
branch_labels = None
depends_on = None


def upgrade():
    """Add created_at column to llm_telemetry and populate existing rows."""
    # 1. Add column allowing NULLs first
    with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # 2. Update existing rows with current UTC timestamp
    # Using CURRENT_TIMESTAMP for portability; in Postgres it maps to NOW()
    op.execute("UPDATE llm_telemetry SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    # 3. Alter column to disallow NULLs
    with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
        batch_op.alter_column('created_at', nullable=False)


def downgrade():
    """Remove created_at column from llm_telemetry."""
    with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
        batch_op.drop_column('created_at')
