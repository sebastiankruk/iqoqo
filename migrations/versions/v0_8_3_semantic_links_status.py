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
"""Add status column to semantic_links table.

Lifecycle states: 'accepted', 'suggested', 'rejected'. Default 'accepted'.

Revision ID: v0_8_3_semantic_links_status
Revises: v0_8_3_duplicate_expression_tier
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_3_semantic_links_status"
down_revision = "v0_8_3_duplicate_expression_tier"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    catalog_schema = "catalog" if is_pg else None

    op.add_column(
        "semantic_links",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="accepted"),
        schema=catalog_schema,
    )
    op.create_index(
        "ix_semantic_links_status",
        "semantic_links",
        ["status"],
        schema=catalog_schema,
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    catalog_schema = "catalog" if is_pg else None

    op.drop_index("ix_semantic_links_status", table_name="semantic_links", schema=catalog_schema)
    op.drop_column("semantic_links", "status", schema=catalog_schema)
