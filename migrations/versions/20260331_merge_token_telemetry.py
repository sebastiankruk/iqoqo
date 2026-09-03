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
"""Merge token_blocklist and operation_type branches

Revision ID: 20260331_merge_token_and_telemetry_branches
Revises: d2be8499d439, 20260330_add_operation_type_to_llm_telemetry
Create Date: 2026-03-31 10:00:00.000000

"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "20260331_merge_token_and_telemetry_branches"
down_revision = ("d2be8499d439", "20260330_add_operation_type_to_llm_telemetry")
branch_labels = None
depends_on = None


def upgrade():
    """Merge point — no schema changes."""


def downgrade():
    """Merge point — no schema changes."""
