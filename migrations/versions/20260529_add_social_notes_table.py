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

"""Add social notes table.

Revision ID: 20260529_add_social_notes
Revises: 20260525_add_social_feedbacks
Create Date: 2026-05-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260529_add_social_notes'
down_revision = '20260525_add_social_feedbacks'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create the social_notes table
    op.create_table('social_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('work_id', sa.Integer(), nullable=True),
        sa.Column('expression_id', sa.Integer(), nullable=True),
        sa.Column('manifestation_id', sa.Integer(), nullable=True),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_id'], ['catalog.works.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expression_id'], ['catalog.expressions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['manifestation_id'], ['catalog.manifestations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['inventory.items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "(case when work_id is not null then 1 else 0 end + "
            "case when expression_id is not null then 1 else 0 end + "
            "case when manifestation_id is not null then 1 else 0 end + "
            "case when item_id is not null then 1 else 0 end) = 1",
            name="chk_note_target_exactly_one",
        ),
        schema='inventory'
    )
    with op.batch_alter_table('social_notes', schema='inventory') as batch_op:
        batch_op.create_index(batch_op.f('ix_inventory_social_notes_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_social_notes_work_id'), ['work_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_social_notes_expression_id'), ['expression_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_social_notes_manifestation_id'), ['manifestation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_inventory_social_notes_item_id'), ['item_id'], unique=False)

def downgrade():
    op.drop_table('social_notes', schema='inventory')
