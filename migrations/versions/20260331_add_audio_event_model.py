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
"""Add audio event-based models to catalog schema

Revision ID: 20260331_add_audio_event_model
Revises: 20260331_move_frbr_to_catalog_schema
Create Date: 2026-03-31 12:00:00.000000

Creates the following tables in the ``catalog`` schema:

- ``catalog.contributors``            — FRBRoo F10 Person / F11 Corporate Body
- ``catalog.work_contributions``      — FRBRoo Composition Event
- ``catalog.expression_contributions`` — FRBRoo Performance Event
- ``catalog.work_parts``              — FRBRoo F15 Complex Work containment

All FK references target ``catalog.*`` tables.  Cascade DELETE is set on
every child FK so that removing a Work/Expression also cleans up its
contribution records and work-part links.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_add_audio_event_model"
down_revision = "20260331_move_frbr_to_catalog_schema"
branch_labels = None
depends_on = None


def upgrade():
    """Create audio event tables in the catalog schema."""
    # Ensure the catalog schema exists (created by previous migration, but
    # safe to be idempotent here too).
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")

    # ------------------------------------------------------------------
    # catalog.contributors
    # ------------------------------------------------------------------
    op.create_table(
        "contributors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="person"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="catalog",
    )
    op.create_index("ix_contributors_name", "contributors", ["name"], schema="catalog")

    # ------------------------------------------------------------------
    # catalog.work_contributions  (FRBRoo Composition Event)
    # ------------------------------------------------------------------
    op.create_table(
        "work_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.Integer(), nullable=False),
        sa.Column("contributor_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["contributor_id"], ["catalog.contributors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_id"], ["catalog.works.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="catalog",
    )
    op.create_index("ix_work_contributions_work_id", "work_contributions", ["work_id"], schema="catalog")
    op.create_index("ix_work_contributions_contributor_id", "work_contributions", ["contributor_id"], schema="catalog")

    # ------------------------------------------------------------------
    # catalog.expression_contributions  (FRBRoo Performance Event)
    # ------------------------------------------------------------------
    op.create_table(
        "expression_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expression_id", sa.Integer(), nullable=False),
        sa.Column("contributor_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["contributor_id"], ["catalog.contributors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expression_id"], ["catalog.expressions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="catalog",
    )
    op.create_index(
        "ix_expression_contributions_expression_id",
        "expression_contributions",
        ["expression_id"],
        schema="catalog",
    )
    op.create_index(
        "ix_expression_contributions_contributor_id",
        "expression_contributions",
        ["contributor_id"],
        schema="catalog",
    )

    # ------------------------------------------------------------------
    # catalog.work_parts  (FRBRoo F15 Complex Work — box-set containment)
    # ------------------------------------------------------------------
    op.create_table(
        "work_parts",
        sa.Column("container_work_id", sa.Integer(), nullable=False),
        sa.Column("part_work_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["container_work_id"], ["catalog.works.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_work_id"], ["catalog.works.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("container_work_id", "part_work_id"),
        schema="catalog",
    )
    op.create_index("ix_work_parts_container_work_id", "work_parts", ["container_work_id"], schema="catalog")
    op.create_index("ix_work_parts_part_work_id", "work_parts", ["part_work_id"], schema="catalog")


def downgrade():
    """Drop audio event tables from the catalog schema."""
    op.drop_index("ix_work_parts_part_work_id", table_name="work_parts", schema="catalog")
    op.drop_index("ix_work_parts_container_work_id", table_name="work_parts", schema="catalog")
    op.drop_table("work_parts", schema="catalog")

    op.drop_index(
        "ix_expression_contributions_contributor_id",
        table_name="expression_contributions",
        schema="catalog",
    )
    op.drop_index(
        "ix_expression_contributions_expression_id",
        table_name="expression_contributions",
        schema="catalog",
    )
    op.drop_table("expression_contributions", schema="catalog")

    op.drop_index("ix_work_contributions_contributor_id", table_name="work_contributions", schema="catalog")
    op.drop_index("ix_work_contributions_work_id", table_name="work_contributions", schema="catalog")
    op.drop_table("work_contributions", schema="catalog")

    op.drop_index("ix_contributors_name", table_name="contributors", schema="catalog")
    op.drop_table("contributors", schema="catalog")
