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
"""Add catalog.semantic_links table for Linked Open Data entity reconciliation.

Revision ID: v0_8_2_semantic_links
Revises: v0_8_1_oauth_exchange_codes
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_2_semantic_links"
down_revision = "v0_8_1_oauth_exchange_codes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    catalog_schema = "catalog" if is_pg else None

    op.create_table(
        "semantic_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("authority", sa.String(length=50), nullable=False),
        sa.Column("external_uri", sa.String(length=2048), nullable=False),
        sa.Column("pref_label", sa.String(length=500), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("match_strategy", sa.String(length=50), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        schema=catalog_schema,
    )

    op.create_index(
        "ix_semantic_links_entity",
        "semantic_links",
        ["entity_type", "entity_id"],
        schema=catalog_schema,
    )
    op.create_index(
        "ix_semantic_links_authority_uri",
        "semantic_links",
        ["authority", "external_uri"],
        schema=catalog_schema,
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    catalog_schema = "catalog" if is_pg else None

    op.drop_index("ix_semantic_links_authority_uri", table_name="semantic_links", schema=catalog_schema)
    op.drop_index("ix_semantic_links_entity", table_name="semantic_links", schema=catalog_schema)
    op.drop_table("semantic_links", schema=catalog_schema)
