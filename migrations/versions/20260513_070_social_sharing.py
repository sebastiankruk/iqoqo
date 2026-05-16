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
"""Add social, privacy fields, and shared_collections for v0.7.0.

Revision ID: 070_social_sharing
Revises: ca691f79cb37
Create Date: 2026-05-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '070_social_sharing'
down_revision = 'ca691f79cb37'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Update Users Table in 'auth' schema
    op.add_column('users', sa.Column('public_username', sa.String(length=50), nullable=True), schema='auth')
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True), schema='auth')
    op.create_unique_constraint('uq_users_public_username', 'users', ['public_username'], schema='auth')
    op.create_index('ix_users_public_visibility', 'users', ['public_username', 'visibility'], schema='auth')

    # 2. Update Items Table in 'inventory' schema
    op.add_column('items', sa.Column('is_hidden', sa.Boolean(), server_default='false', nullable=False), schema='inventory')
    op.create_index('ix_items_owner_hidden', 'items', ['owner_id', 'is_hidden'], schema='inventory')

    # 3. Create Shared Collections Table in 'inventory' schema
    op.create_table('shared_collections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('share_token', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token'),
        schema='inventory'
    )

def downgrade():
    # Drop Shared Collections
    op.drop_table('shared_collections', schema='inventory')

    # Revert Items
    op.drop_index('ix_items_owner_hidden', table_name='items', schema='inventory')
    op.drop_column('items', 'is_hidden', schema='inventory')

    # Revert Users
    op.drop_index('ix_users_public_visibility', table_name='users', schema='auth')
    op.drop_constraint('uq_users_public_username', 'users', type_='unique', schema='auth')
    op.drop_column('users', 'bio', schema='auth')
    op.drop_column('users', 'public_username', schema='auth')
