"""Merge migration branches

Revision ID: 9549d8c37cbc
Revises: 012982fb9fe5, 20260311_fts
Create Date: 2026-03-15 21:28:01.835028

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
revision = "9549d8c37cbc"
down_revision = ("012982fb9fe5", "20260311_fts")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
