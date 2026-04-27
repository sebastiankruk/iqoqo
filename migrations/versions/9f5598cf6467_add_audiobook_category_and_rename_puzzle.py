"""add_audiobook_category_and_rename_puzzle

Revision ID: 9f5598cf6467
Revises: 88d8fcbeb3df
Create Date: 2026-04-27 22:34:57.648427

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f5598cf6467'
down_revision = '88d8fcbeb3df'
branch_labels = None
depends_on = None


def upgrade():
    """Move audiobook manifestations to the new audiobook category and rename puzzle format."""
    conn = op.get_bind()
    prefix_catalog = "catalog." if conn.dialect.name == "postgresql" else ""

    # 1. Update expressions content_type for audiobooks
    # manifestations with audiobook formats should point to expressions of type 'audiobook'
    op.execute(f"""
        UPDATE {prefix_catalog}expressions 
        SET content_type = 'audiobook' 
        WHERE id IN (
            SELECT expression_id 
            FROM {prefix_catalog}manifestations 
            WHERE meta->>'format' IN ('audiobook_cd', 'audiobook_cassette', 'audiobook_digital')
        )
    """)

    # 2. Rename 'puzzle' format to 'jigsaw_puzzle' in manifestation meta
    # We use jsonb_set for Postgres, with explicit casts if needed
    if conn.dialect.name == "postgresql":
        op.execute(f"""
            UPDATE {prefix_catalog}manifestations 
            SET meta = jsonb_set(meta::jsonb, '{{format}}', '"jigsaw_puzzle"')::json 
            WHERE meta->>'format' = 'puzzle'
        """)
    else:
        # SQLite or other: simpler but potentially slower or needs JSON functions if available
        # Since the project rules mention Postgres explicitly (prefix = "catalog."), 
        # we prioritize it. For others we can try a basic replace if supported.
        pass


def downgrade():
    """Revert audiobook category move and puzzle rename."""
    conn = op.get_bind()
    prefix_catalog = "catalog." if conn.dialect.name == "postgresql" else ""

    # 1. Revert 'audiobook' category to 'text' (best effort)
    op.execute(f"UPDATE {prefix_catalog}expressions SET content_type = 'text' WHERE content_type = 'audiobook'")

    # 2. Revert 'jigsaw_puzzle' format to 'puzzle'
    if conn.dialect.name == "postgresql":
        op.execute(f"""
            UPDATE {prefix_catalog}manifestations 
            SET meta = jsonb_set(meta::jsonb, '{{format}}', '"puzzle"')::json 
            WHERE meta->>'format' = 'jigsaw_puzzle'
        """)
