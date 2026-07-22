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

"""Add escalation requests table.

Revision ID: 20260722_add_escalation_requests
Revises: 20260709_defer_tsvector
Create Date: 2026-07-22 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260722_add_escalation_requests"
down_revision = "20260709_defer_tsvector"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create the escalation_requests table
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("escalation_requests", schema="inventory"):
        op.create_table(
            "escalation_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("work_id", sa.Integer(), nullable=True),
            sa.Column("expression_id", sa.Integer(), nullable=True),
            sa.Column("manifestation_id", sa.Integer(), nullable=True),
            sa.Column("item_id", sa.Integer(), nullable=True),
            sa.Column("field_name", sa.String(length=100), nullable=False),
            sa.Column("current_value", sa.Text(), nullable=True),
            sa.Column("suggested_value", sa.Text(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
            sa.Column("resolved_by", sa.UUID(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["resolved_by"], ["auth.users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["work_id"], ["catalog.works.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["expression_id"], ["catalog.expressions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["manifestation_id"], ["catalog.manifestations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["inventory.items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) = 1",
                name="chk_escalation_target_exactly_one",
            ),
            sa.CheckConstraint(
                "status IN ('pending', 'accepted', 'rejected', 'duplicate')",
                name="chk_escalation_status_valid",
            ),
            schema="inventory",
        )
        with op.batch_alter_table("escalation_requests", schema="inventory") as batch_op:
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_user_id"), ["user_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_status"), ["status"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_work_id"), ["work_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_expression_id"), ["expression_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_manifestation_id"), ["manifestation_id"], unique=False)
            batch_op.create_index(batch_op.f("ix_inventory_escalation_requests_item_id"), ["item_id"], unique=False)


def downgrade():
    op.drop_table("escalation_requests", schema="inventory")
