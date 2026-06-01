"""add_apple_id_to_users

Revision ID: 01427dc94f42
Revises: 20260529_add_social_notes
Create Date: 2026-05-31 17:38:08.335661

"""

import sqlalchemy as sa

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

# revision identifiers, used by Alembic.
revision = "01427dc94f42"
down_revision = "20260529_add_social_notes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("apple_id", sa.String(255), unique=True, nullable=True), schema="auth")
    op.create_index("ix_users_apple_id", "users", ["apple_id"], unique=True, schema="auth")


def downgrade():
    op.drop_index("ix_users_apple_id", table_name="users", schema="auth")
    op.drop_column("users", "apple_id", schema="auth")
