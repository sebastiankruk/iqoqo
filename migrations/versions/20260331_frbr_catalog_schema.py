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
"""Move core FRBR tables from public to catalog schema

Revision ID: 20260331_frbr_catalog_schema
Revises: 20260331_merge_token_telemetry
Create Date: 2026-03-31 11:00:00.000000

Moves works, expressions, manifestations, and items from the default
``public`` schema into the dedicated ``catalog`` schema.  All foreign-key
references that cross schema boundaries (items.owner_id → public.users.id)
are preserved — PostgreSQL FKs are schema-aware.

The GIN full-text search indexes are automatically preserved by PostgreSQL
during an ALTER TABLE SET SCHEMA operation, so no explicit index recreation
is required.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_frbr_catalog_schema"
down_revision = "20260331_merge_token_telemetry"
branch_labels = None
depends_on = None

_FRBR_TABLES = ("works", "expressions", "manifestations", "items")


def upgrade():
    """Create the catalog schema and move FRBR tables into it."""
    # Create the catalog schema (idempotent)
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")

    # Move each FRBR table from public → catalog.
    # PostgreSQL preserves all indexes, constraints, and sequences.
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    for table in _FRBR_TABLES:
        if is_postgres:
            # Check if table already exists in catalog schema
            res = conn.execute(
                sa.text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'catalog' AND table_name = '{table}')"
                )
            ).scalar()

            if res:
                # If table already exists in catalog, drop it in public if it exists there
                op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
            else:
                # If it doesn't exist in catalog, but exists in public, move it
                res_public = conn.execute(
                    sa.text(
                        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table}')"
                    )
                ).scalar()
                if res_public:
                    op.execute(f"ALTER TABLE public.{table} SET SCHEMA catalog")
        else:
            op.execute(f"ALTER TABLE public.{table} SET SCHEMA catalog")


def downgrade():
    """Move FRBR tables back to public schema."""
    for table in reversed(_FRBR_TABLES):
        op.execute(f"ALTER TABLE catalog.{table} SET SCHEMA public")

    # Drop the schema only if it is now empty.
    op.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'catalog'
                ) THEN
                    DROP SCHEMA catalog;
                END IF;
            END $$;
            """))
