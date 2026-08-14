# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Add local feedback tickets."""

import sqlalchemy as sa
from alembic import op

revision = "20260813_add_feedback_items"
down_revision = ("e3f891ab45c2", "b7ad7843fb4a")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feedback_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("feedback_type IN ('feature_request', 'bug')", name="chk_feedback_item_type"),
        sa.CheckConstraint("status IN ('new', 'accepted', 'in_progress', 'in_validation', 'closed')", name="chk_feedback_item_status"),
        schema="inventory",
    )
    op.create_index("ix_inventory_feedback_items_user_id", "feedback_items", ["user_id"], schema="inventory")
    op.create_index("ix_inventory_feedback_items_status", "feedback_items", ["status"], schema="inventory")


def downgrade():
    op.drop_table("feedback_items", schema="inventory")
