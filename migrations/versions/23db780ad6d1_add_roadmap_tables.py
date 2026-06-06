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

"""add roadmap tables

Revision ID: 23db780ad6d1
Revises: 20260529_add_social_notes
Create Date: 2026-06-04 20:25:07.115688

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '23db780ad6d1'
down_revision = '20260529_add_social_notes'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reading_roadmaps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='catalog'
    )
    op.create_table('roadmap_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('roadmap_id', sa.Integer(), nullable=False),
    sa.Column('work_id', sa.Integer(), nullable=True),
    sa.Column('manifestation_id', sa.Integer(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('target_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['manifestation_id'], ['catalog.manifestations.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['roadmap_id'], ['catalog.reading_roadmaps.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['work_id'], ['catalog.works.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    schema='catalog'
    )


def downgrade():
    op.drop_table('roadmap_items', schema='catalog')
    op.drop_table('reading_roadmaps', schema='catalog')
