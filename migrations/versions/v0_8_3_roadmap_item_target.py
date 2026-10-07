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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Add item_id FK to roadmap_items with 4-level FRBR constraint and RESTRICT FKs.

Revision ID: v0_8_3_roadmap_item_target
Revises: v0_8_3_account_lifecycle
Create Date: 2026-10-07

This migration adds an ``item_id`` foreign key to ``catalog.roadmap_items``
so reading roadmaps can target an exact owned physical copy (FRBR Item).
A CHECK constraint enforces that each roadmap item references exactly one
of Work, Expression, Manifestation, or Item.
All target FKs are updated to ``RESTRICT`` to prevent silent deletion or
nulling of roadmap references when catalog/inventory entities are deleted.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_8_3_roadmap_item_target"
down_revision = "v0_8_3_account_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_cat = "catalog" if is_pg else None
    s_inv = "inventory" if is_pg else None

    # STEP 1: Preflight existing rows in roadmap_items.
    # Exactly one of (work_id, expression_id, manifestation_id) must be non-null.
    roadmap_items = sa.table(
        "roadmap_items",
        sa.column("id", sa.Integer),
        sa.column("work_id", sa.Integer),
        sa.column("expression_id", sa.Integer),
        sa.column("manifestation_id", sa.Integer),
        schema=s_cat,
    )
    cardinality_expr = (
        sa.case((roadmap_items.c.work_id.isnot(None), 1), else_=0)
        + sa.case((roadmap_items.c.expression_id.isnot(None), 1), else_=0)
        + sa.case((roadmap_items.c.manifestation_id.isnot(None), 1), else_=0)
    )
    invalid_rows = bind.execute(
        sa.select(roadmap_items.c.id).where(cardinality_expr != 1)
    ).scalars().all()
    if invalid_rows:
        raise ValueError(
            f"Preflight failed: found {len(invalid_rows)} roadmap_items rows with invalid cardinality (IDs: {invalid_rows}). "
            "Resolve invalid target references before upgrading."
        )

    # STEP 2: Add item_id column
    with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
        batch_op.add_column(
            sa.Column("item_id", sa.Integer, nullable=True)
        )

    # STEP 3: Create index on item_id
    idx_name = "ix_catalog_roadmap_items_item_id" if is_pg else "ix_roadmap_items_item_id"
    op.create_index(
        idx_name,
        "roadmap_items",
        ["item_id"],
        schema=s_cat,
    )

    # STEP 4: Update foreign keys to RESTRICT
    if is_pg:
        inspector = sa.inspect(bind)
        fks = inspector.get_foreign_keys("roadmap_items", schema=s_cat)
        for fk in fks:
            fk_name = fk.get("name")
            constrained_cols = fk.get("constrained_columns", [])
            if "work_id" in constrained_cols:
                op.drop_constraint(fk_name, "roadmap_items", schema=s_cat, type_="foreignkey")
            elif "expression_id" in constrained_cols:
                op.drop_constraint(fk_name, "roadmap_items", schema=s_cat, type_="foreignkey")
            elif "manifestation_id" in constrained_cols:
                op.drop_constraint(fk_name, "roadmap_items", schema=s_cat, type_="foreignkey")

        op.create_foreign_key(
            "fk_roadmap_items_work_id",
            "roadmap_items",
            "works",
            ["work_id"],
            ["id"],
            ondelete="RESTRICT",
            source_schema=s_cat,
            referent_schema=s_cat,
        )
        op.create_foreign_key(
            "fk_roadmap_items_expression_id",
            "roadmap_items",
            "expressions",
            ["expression_id"],
            ["id"],
            ondelete="RESTRICT",
            source_schema=s_cat,
            referent_schema=s_cat,
        )
        op.create_foreign_key(
            "fk_roadmap_items_manifestation_id",
            "roadmap_items",
            "manifestations",
            ["manifestation_id"],
            ["id"],
            ondelete="RESTRICT",
            source_schema=s_cat,
            referent_schema=s_cat,
        )
        op.create_foreign_key(
            "fk_roadmap_items_item_id",
            "roadmap_items",
            "items",
            ["item_id"],
            ["id"],
            ondelete="RESTRICT",
            source_schema=s_cat,
            referent_schema=s_inv,
        )
    else:
        with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
            batch_op.create_foreign_key(
                "fk_roadmap_items_item_id",
                "items",
                ["item_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    # STEP 5: Recreate CHECK constraint for 4 FRBR levels (PostgreSQL only)
    if is_pg:
        op.drop_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            schema=s_cat,
            type_="check",
        )
        op.create_check_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            "(CASE WHEN work_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN expression_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN manifestation_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN item_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            schema=s_cat,
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_cat = "catalog" if is_pg else None

    # STEP 1: Preflight check - abort if any item_id target exists
    roadmap_items = sa.table(
        "roadmap_items",
        sa.column("id", sa.Integer),
        sa.column("item_id", sa.Integer),
        schema=s_cat,
    )
    count_item_targets = bind.execute(
        sa.select(sa.func.count(roadmap_items.c.id)).where(roadmap_items.c.item_id.isnot(None))  # pylint: disable=not-callable
    ).scalar() or 0

    if count_item_targets > 0:
        raise ValueError(
            f"Cannot downgrade migration while {count_item_targets} roadmap items target an item_id. "
            "Remove or reassign all Item-targeted roadmap entries before downgrading."
        )

    # STEP 2: Restore 3-level CHECK constraint (PostgreSQL only)
    if is_pg:
        op.drop_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            schema=s_cat,
            type_="check",
        )
        op.create_check_constraint(
            "check_roadmap_item_single_frbr_level",
            "roadmap_items",
            "(CASE WHEN work_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN expression_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN manifestation_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            schema=s_cat,
        )

        # Restore prior foreign key actions (SET NULL)
        inspector = sa.inspect(bind)
        fks = inspector.get_foreign_keys("roadmap_items", schema=s_cat)
        for fk in fks:
            fk_name = fk.get("name")
            constrained_cols = fk.get("constrained_columns", [])
            if any(c in constrained_cols for c in ["work_id", "expression_id", "manifestation_id", "item_id"]):
                op.drop_constraint(fk_name, "roadmap_items", schema=s_cat, type_="foreignkey")

        op.create_foreign_key(
            "fk_roadmap_items_work_id",
            "roadmap_items",
            "works",
            ["work_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=s_cat,
            referent_schema=s_cat,
        )
        op.create_foreign_key(
            "fk_roadmap_items_expression_id",
            "roadmap_items",
            "expressions",
            ["expression_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=s_cat,
            referent_schema=s_cat,
        )
        op.create_foreign_key(
            "fk_roadmap_items_manifestation_id",
            "roadmap_items",
            "manifestations",
            ["manifestation_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=s_cat,
            referent_schema=s_cat,
        )

    # STEP 3: Drop index and column
    idx_name = "ix_catalog_roadmap_items_item_id" if is_pg else "ix_roadmap_items_item_id"
    op.drop_index(idx_name, table_name="roadmap_items", schema=s_cat)

    with op.batch_alter_table("roadmap_items", schema=s_cat) as batch_op:
        if not is_pg:
            batch_op.drop_constraint("fk_roadmap_items_item_id", type_="foreignkey")
        batch_op.drop_column("item_id")
