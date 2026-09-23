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
"""Add expression_id and manifestation_id to user_work_intents for F2/F3 binding.

Revision ID: v0_8_1_wishlist_f2_f3_binding
Revises: v0_7_19_f3_column_promotion
Create Date: 2026-09-23

This migration extends UserWorkIntent with optional foreign keys to
catalog.expressions (F2) and catalog.manifestations (F3), enabling wishlist
entries to target specific editions, translations, or container media
(F15 Complex Works, F16 Container Works).

The composite unique constraint is replaced: the old uq_user_work_intent
(user_id, work_id) is dropped and a new uq_user_work_intent_target
(user_id, work_id, expression_id, manifestation_id) is created.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_8_1_wishlist_f2_f3_binding"
down_revision = "v0_7_19_f3_column_promotion"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_inv = "inventory" if is_pg else None
    s_cat = "catalog" if is_pg else None

    # Determine FK target table prefixes
    expr_table = f"{s_cat}." if s_cat else ""
    manif_table = f"{s_cat}." if s_cat else ""

    # STEP 1: Add expression_id column
    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.add_column(
            sa.Column("expression_id", sa.Integer, nullable=True)
        )
        batch_op.add_column(
            sa.Column("manifestation_id", sa.Integer, nullable=True)
        )

    # STEP 2: Create indexes on new columns
    ix_expr = "ix_inventory_user_work_intents_expression_id" if is_pg else "ix_user_work_intents_expression_id"
    ix_manif = "ix_inventory_user_work_intents_manifestation_id" if is_pg else "ix_user_work_intents_manifestation_id"

    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.create_index(ix_expr, ["expression_id"])
        batch_op.create_index(ix_manif, ["manifestation_id"])

    # STEP 3: Create foreign keys
    fk_expr = "fk_user_work_intents_expression_id"
    fk_manif = "fk_user_work_intents_manifestation_id"

    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.create_foreign_key(
            fk_expr,
            f"{expr_table}expressions",
            ["expression_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            fk_manif,
            f"{manif_table}manifestations",
            ["manifestation_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # STEP 4: Drop old unique constraint and create new one
    # The old constraint name is uq_user_work_intent
    # Use partial unique indexes on PostgreSQL to handle NULLs correctly
    # (NULL != NULL in SQL, so a composite unique constraint would allow
    # duplicate rows where expression_id or manifestation_id is NULL).
    uq_new = "uq_user_work_intent_target"

    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.drop_constraint("uq_user_work_intent", type_="unique")

    if is_pg:
        # PostgreSQL: partial unique indexes for each NULL-combination
        op.create_index(
            "uq_user_intent_work_only",
            "user_work_intents",
            ["user_id", "work_id"],
            unique=True,
            postgresql_where=sa.text("expression_id IS NULL AND manifestation_id IS NULL"),
            schema=s_inv,
        )
        op.create_index(
            "uq_user_intent_work_expr",
            "user_work_intents",
            ["user_id", "work_id", "expression_id"],
            unique=True,
            postgresql_where=sa.text("manifestation_id IS NULL"),
            schema=s_inv,
        )
        op.create_index(
            uq_new,
            "user_work_intents",
            ["user_id", "work_id", "expression_id", "manifestation_id"],
            unique=True,
            schema=s_inv,
        )
    else:
        # SQLite: batch_alter_table doesn't support partial indexes;
        # fall back to the composite unique constraint (weaker NULL handling).
        with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
            batch_op.create_unique_constraint(
                uq_new,
                ["user_id", "work_id", "expression_id", "manifestation_id"],
            )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    s_inv = "inventory" if is_pg else None

    # STEP 1: Drop new unique constraint/indexes and restore old one
    if is_pg:
        op.drop_index("uq_user_work_intent_target", table_name="user_work_intents", schema=s_inv)
        op.drop_index("uq_user_intent_work_expr", table_name="user_work_intents", schema=s_inv)
        op.drop_index("uq_user_intent_work_only", table_name="user_work_intents", schema=s_inv)
    else:
        with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
            batch_op.drop_constraint("uq_user_work_intent_target", type_="unique")

    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.create_unique_constraint(
            "uq_user_work_intent",
            ["user_id", "work_id"],
        )

    # STEP 2: Drop foreign keys
    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.drop_constraint("fk_user_work_intents_manifestation_id", type_="foreignkey")
        batch_op.drop_constraint("fk_user_work_intents_expression_id", type_="foreignkey")

    # STEP 3: Drop indexes
    ix_expr = "ix_inventory_user_work_intents_expression_id" if is_pg else "ix_user_work_intents_expression_id"
    ix_manif = "ix_inventory_user_work_intents_manifestation_id" if is_pg else "ix_user_work_intents_manifestation_id"

    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.drop_index(ix_manif)
        batch_op.drop_index(ix_expr)

    # STEP 4: Drop columns
    with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
        batch_op.drop_column("manifestation_id")
        batch_op.drop_column("expression_id")
