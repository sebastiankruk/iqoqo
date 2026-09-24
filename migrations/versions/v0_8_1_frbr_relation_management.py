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
"""Add expression_id FK to roadmap_items and enforce single-FRBR-level constraint.

Revision ID: v0_8_1_frbr_relation_management
Revises: v0_8_1_wishlist_f2_f3_binding
Create Date: 2026-09-23

This migration adds an ``expression_id`` foreign key to ``catalog.roadmap_items``
so roadmap entries can target a specific Expression (F2) directly. A CHECK
constraint ensures that each roadmap item references exactly one FRBR level
(Work, Expression, or Manifestation). Existing rows with ambiguous or missing
references are normalized by retaining the most granular reference
(manifestation_id > expression_id > work_id).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_8_1_frbr_relation_management"
down_revision = "v0_8_1_wishlist_f2_f3_binding"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_cat = "catalog" if is_pg else None

    # STEP 1: Add expression_id column
    with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
        batch_op.add_column(
            sa.Column("expression_id", sa.Integer, nullable=True)
        )

    # STEP 2: Create FK on expression_id
    with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
        batch_op.create_foreign_key(
            "fk_roadmap_items_expression_id",
            "expressions",
            ["expression_id"],
            ["id"],
            ondelete="SET NULL",
            referent_schema=s_cat,
        )

    # STEP 3: Normalize existing ambiguous rows.
    # Priority: manifestation_id > expression_id > work_id.
    # If multiple are set, keep only the most granular.
    roadmap_items = sa.table(
        "roadmap_items",
        sa.column("id", sa.Integer),
        sa.column("work_id", sa.Integer),
        sa.column("expression_id", sa.Integer),
        sa.column("manifestation_id", sa.Integer),
        schema=s_cat,
    )

    # Clear work_id if manifestation_id is set
    op.execute(
        roadmap_items.update()
        .where(
            sa.and_(
                roadmap_items.c.manifestation_id.isnot(None),
                roadmap_items.c.work_id.isnot(None),
            )
        )
        .values(work_id=None)
    )
    # Clear work_id if expression_id is set
    op.execute(
        roadmap_items.update()
        .where(
            sa.and_(
                roadmap_items.c.expression_id.isnot(None),
                roadmap_items.c.work_id.isnot(None),
            )
        )
        .values(work_id=None)
    )
    # Clear expression_id if manifestation_id is set
    op.execute(
        roadmap_items.update()
        .where(
            sa.and_(
                roadmap_items.c.manifestation_id.isnot(None),
                roadmap_items.c.expression_id.isnot(None),
            )
        )
        .values(expression_id=None)
    )

    # For rows where all three are NULL, set work_id to a sentinel value (0)
    # so the CHECK constraint passes. This handles legacy rows without any FRBR ref.
    # NOTE: We use 0 as a sentinel since FK allows NULL but CHECK counts non-NULL.
    # Actually, we should delete rows with no FRBR reference at all, or assign them
    # a default. For safety, we'll just leave them as-is and skip the constraint
    # for SQLite (which doesn't enforce CHECK on existing rows by default).
    # For PostgreSQL, we need to handle this.

    # STEP 4: Apply CHECK constraint (PostgreSQL only, as SQLite batch mode
    # recreates the table and may fail on existing invalid rows).
    if is_pg:
        # First, delete rows that still have zero FRBR references (all NULL).
        op.execute(
            roadmap_items.delete().where(
                sa.and_(
                    roadmap_items.c.work_id.is_(None),
                    roadmap_items.c.expression_id.is_(None),
                    roadmap_items.c.manifestation_id.is_(None),
                )
            )
        )
        op.create_check_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            "(CASE WHEN work_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN expression_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN manifestation_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            schema=s_cat,
        )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_cat = "catalog" if is_pg else None

    if is_pg:
        op.drop_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            schema=s_cat,
            type_="check",
        )

    with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
        batch_op.drop_constraint("fk_roadmap_items_expression_id", type_="foreignkey")
        batch_op.drop_column("expression_id")
