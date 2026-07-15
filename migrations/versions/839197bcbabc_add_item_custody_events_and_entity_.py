"""add_item_custody_events_and_entity_audit_logs

Revision ID: 839197bcbabc
Revises: 3177c5e97570
Create Date: 2026-07-15 09:03:35.697632

Adds:
- inventory.item_custody_events — CIDOC CRM-compliant immutable custody log (Item tier)
- inventory.entity_audit_logs  — Curation/merge audit log (Work/Expression/Manifestation tiers)
"""

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
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "839197bcbabc"
down_revision = "3177c5e97570"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "entity_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("change_type", sa.String(length=100), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )
    with op.batch_alter_table("entity_audit_logs", schema="inventory") as batch_op:
        batch_op.create_index("ix_entity_audit_logs_entity", ["entity_type", "entity_id"], unique=False)
        batch_op.create_index("ix_entity_audit_logs_logged_at", ["logged_at"], unique=False)

    op.create_table(
        "item_custody_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["auth.users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["item_id"], ["inventory.items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="inventory",
    )
    with op.batch_alter_table("item_custody_events", schema="inventory") as batch_op:
        batch_op.create_index("ix_item_custody_events_item_id", ["item_id"], unique=False)
        batch_op.create_index("ix_item_custody_events_recorded_at", ["recorded_at"], unique=False)


def downgrade():
    with op.batch_alter_table("item_custody_events", schema="inventory") as batch_op:
        batch_op.drop_index("ix_item_custody_events_recorded_at")
        batch_op.drop_index("ix_item_custody_events_item_id")

    op.drop_table("item_custody_events", schema="inventory")

    with op.batch_alter_table("entity_audit_logs", schema="inventory") as batch_op:
        batch_op.drop_index("ix_entity_audit_logs_logged_at")
        batch_op.drop_index("ix_entity_audit_logs_entity")

    op.drop_table("entity_audit_logs", schema="inventory")
