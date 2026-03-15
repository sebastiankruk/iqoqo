"""Merge migration branches

Revision ID: 9549d8c37cbc
Revises: 012982fb9fe5, 20260311_fts
Create Date: 2026-03-15 21:28:01.835028

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9549d8c37cbc'
down_revision = ('012982fb9fe5', '20260311_fts')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
