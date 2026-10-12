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
"""Create work_series_memberships table.

Revision ID: v0_8_4_work_series_mem
Revises: v0_8_4_search_unaccent
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "v0_8_4_work_series_mem"
down_revision = "v0_8_4_search_unaccent"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    schema = "catalog" if is_pg else None
    catalog_pfx = "catalog." if is_pg else ""

    op.create_table(
        "work_series_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("series_work_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["work_id"],
            [f"{catalog_pfx}works.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["series_work_id"],
            [f"{catalog_pfx}works.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id", "series_work_id", name="uq_work_series_membership"),
        schema=schema,
    )
    op.create_index(
        "ix_work_series_memberships_work_id",
        "work_series_memberships",
        ["work_id"],
        schema=schema,
    )
    op.create_index(
        "ix_work_series_memberships_series_work_id",
        "work_series_memberships",
        ["series_work_id"],
        schema=schema,
    )

    # Backfill from work_parts where container exists
    work_parts_tbl = f"{catalog_pfx}work_parts"
    target_tbl = f"{catalog_pfx}work_series_memberships"
    op.execute(
        f"""
        INSERT INTO {target_tbl} (work_id, series_work_id, sequence)
        SELECT part_work_id, container_work_id, sequence
        FROM {work_parts_tbl}
        ON CONFLICT DO NOTHING
        """
        if is_pg
        else f"""
        INSERT OR IGNORE INTO {target_tbl} (work_id, series_work_id, sequence)
        SELECT part_work_id, container_work_id, sequence
        FROM {work_parts_tbl}
        """
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    schema = "catalog" if is_pg else None

    op.drop_table("work_series_memberships", schema=schema)
