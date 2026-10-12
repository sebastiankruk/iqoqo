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
"""Enable unaccent extension and immutable wrapper function for search.

Revision ID: v0_8_4_search_unaccent
Revises: v0_8_3_item_custody_owners
Create Date: 2026-10-11
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_8_4_search_unaccent"
down_revision = "v0_8_3_item_custody_owners"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        op.execute(
            """
            CREATE OR REPLACE FUNCTION immutable_unaccent(text)
            RETURNS text AS $$
                SELECT public.unaccent($1);
            $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;
            """
        )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
