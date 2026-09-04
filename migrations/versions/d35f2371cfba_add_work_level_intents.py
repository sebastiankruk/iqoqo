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

"""add_work_level_intents

Revision ID: d35f2371cfba
Revises: 20260521_backfill_work_genres
Create Date: 2026-05-24 23:22:17.925140

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d35f2371cfba"
down_revision = "20260521_backfill_work_genres"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def has_index(table_name, index_name, schema=None):
        indexes = inspector.get_indexes(table_name, schema=schema)
        return any(idx["name"] == index_name for idx in indexes)

    # 1. Create the user_work_intents table
    if not inspector.has_table("user_work_intents", schema="inventory"):
        op.create_table(
            "user_work_intents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("work_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["work_id"], ["catalog.works.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "work_id", name="uq_user_work_intent"),
            schema="inventory",
        )
        with op.batch_alter_table("user_work_intents", schema="inventory") as batch_op:
            batch_op.create_index(batch_op.f("ix_inventory_user_work_intents_user_id"), ["user_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_user_work_intents_work_id"), ["work_id"], unique=False)

    # 2. Migrate legacy manifestation-level virtual items to work-level intents
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    insp = sa.inspect(bind)
    schema_name = "inventory" if is_pg else None
    if not insp.has_table("items", schema=schema_name):
        return
    item_cols = {c["name"] for c in insp.get_columns("items", schema=schema_name)}
    if "collection_status" not in item_cols:
        return

    items_table = "inventory.items" if is_pg else "items"
    manifs_table = "catalog.manifestations" if is_pg else "manifestations"
    exprs_table = "catalog.expressions" if is_pg else "expressions"
    intents_table = "inventory.user_work_intents" if is_pg else "user_work_intents"

    select_query = f"""
        SELECT i.owner_id, e.work_id, i.status
        FROM {items_table} i
        JOIN {manifs_table} m ON i.manifestation_id = m.id
        JOIN {exprs_table} e ON m.expression_id = e.id
        WHERE i.collection_status = 'wish_list'
    """

    try:
        rows = bind.execute(sa.text(select_query)).fetchall()

        inserted = set()
        for row in rows:
            user_id, work_id, status = row
            key = (user_id, work_id)
            if key not in inserted:
                p_status = status if status else "want_to_read"
                insert_query = f"""
                    INSERT INTO {intents_table} (user_id, work_id, status)
                    VALUES (:user_id, :work_id, :status)
                """
                bind.execute(sa.text(insert_query), {"user_id": str(user_id), "work_id": work_id, "status": p_status})
                inserted.add(key)

        # Delete legacy wish_list items
        delete_query = f"DELETE FROM {items_table} WHERE collection_status = 'wish_list'"
        bind.execute(sa.text(delete_query))
    except Exception as e:
        print(f"Skipping migration logic due to empty/uninitialized tables: {e}")


def downgrade():
    op.drop_table("user_work_intents", schema="inventory")
