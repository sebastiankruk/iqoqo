"""add_feedback_comments_schema

Revision ID: f65648a6aaf4
Revises: 20260818_add_expansion_links
Create Date: 2026-08-20 13:15:28.941913

"""
import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f65648a6aaf4'
down_revision = '20260818_add_expansion_links'
branch_labels = None
depends_on = None

def upgrade():
    # 0. Ensure schema exists
    op.execute('CREATE SCHEMA IF NOT EXISTS social')

    # 1. Move table to social schema
    op.execute('ALTER TABLE inventory.feedback_items SET SCHEMA social')

    # Rename indexes to match new schema
    op.execute('ALTER INDEX social.ix_inventory_feedback_items_status RENAME TO ix_social_feedback_items_status')
    op.execute('ALTER INDEX social.ix_inventory_feedback_items_user_id RENAME TO ix_social_feedback_items_user_id')

    # 2. Create feedback_comments table
    op.create_table('feedback_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feedback_item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('comment_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['feedback_item_id'], ['social.feedback_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='social'
    )
    op.create_index(op.f('ix_social_feedback_comments_feedback_item_id'), 'feedback_comments', ['feedback_item_id'], unique=False, schema='social')
    op.create_index(op.f('ix_social_feedback_comments_user_id'), 'feedback_comments', ['user_id'], unique=False, schema='social')

    # 3. Migrate JSON data
    op.execute("""
        INSERT INTO social.feedback_comments (feedback_item_id, user_id, comment_text, created_at)
        SELECT 
            i.id as feedback_item_id,
            (c->>'user_id')::uuid as user_id,
            c->>'comment' as comment_text,
            (c->>'created_at')::timestamp as created_at
        FROM social.feedback_items i,
        jsonb_array_elements(i.comments::jsonb) as c
        WHERE i.comments IS NOT NULL AND jsonb_typeof(i.comments::jsonb) = 'array'
    """)

    # 4. Drop comments column from feedback_items
    op.drop_column('feedback_items', 'comments', schema='social')

def downgrade():
    # 1. Recreate JSONB column
    op.add_column('feedback_items', sa.Column('comments', postgresql.JSONB(), server_default='[]', nullable=False), schema='social')

    # 2. Migrate data back
    op.execute("""
        UPDATE social.feedback_items i
        SET comments = (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'user_id', c.user_id,
                    'comment', c.comment_text,
                    'created_at', c.created_at
                )
            ), '[]'::jsonb)
            FROM social.feedback_comments c
            WHERE c.feedback_item_id = i.id
        )
    """)

    # 3. Drop feedback_comments
    op.drop_index(op.f('ix_social_feedback_comments_user_id'), table_name='feedback_comments', schema='social')
    op.drop_index(op.f('ix_social_feedback_comments_feedback_item_id'), table_name='feedback_comments', schema='social')
    op.drop_table('feedback_comments', schema='social')

    # Rename indexes back
    op.execute('ALTER INDEX social.ix_social_feedback_items_status RENAME TO ix_inventory_feedback_items_status')
    op.execute('ALTER INDEX social.ix_social_feedback_items_user_id RENAME TO ix_inventory_feedback_items_user_id')

    # 4. Move table back to inventory schema
    op.execute('ALTER TABLE social.feedback_items SET SCHEMA inventory')
