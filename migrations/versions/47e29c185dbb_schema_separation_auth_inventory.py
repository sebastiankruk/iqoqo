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
"""schema separation auth inventory

Revision ID: 47e29c185dbb
Revises: 20260331_add_audio_event_model
Create Date: 2026-04-03 15:46:06.912180

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "47e29c185dbb"
down_revision = "20260331_add_audio_event_model"
branch_labels = None
depends_on = None


def upgrade():
    """Create auth and inventory schemas and move existing tables."""
    conn = op.get_bind()

    # SQLite does not support schemas natively; this logic only applies to PostgreSQL.
    if conn.dialect.name == "postgresql":
        op.execute("CREATE SCHEMA IF NOT EXISTS auth")
        op.execute("CREATE SCHEMA IF NOT EXISTS inventory")

        # Move auth-related tables from public -> auth
        # Note: These were created in public by earlier migrations.
        tables_auth = ["users", "roles", "permissions", "user_roles", "role_permissions", "token_blocklist", "user_consents"]
        for table in tables_auth:
            # Check if table already exists in auth schema
            res = conn.execute(
                sa.text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = '{table}')")
            ).scalar()
            if res:
                op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
            else:
                res_public = conn.execute(
                    sa.text(
                        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table}')"
                    )
                ).scalar()
                if res_public:
                    op.execute(f"ALTER TABLE public.{table} SET SCHEMA auth")

        # Move items table from catalog -> inventory
        # Note: items was moved to catalog in 20260331_frbr_catalog_schema.py
        res_items = conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'inventory' AND table_name = 'items')")
        ).scalar()
        if res_items:
            op.execute("DROP TABLE IF EXISTS catalog.items CASCADE")
            op.execute("DROP TABLE IF EXISTS public.items CASCADE")
        else:
            res_catalog = conn.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'catalog' AND table_name = 'items')")
            ).scalar()
            if res_catalog:
                op.execute("ALTER TABLE catalog.items SET SCHEMA inventory")
            else:
                res_public = conn.execute(
                    sa.text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'items')"
                    )
                ).scalar()
                if res_public:
                    op.execute("ALTER TABLE public.items SET SCHEMA inventory")


def downgrade():
    """Move tables back and drop schemas."""
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        # Move items table back from inventory -> catalog
        op.execute("ALTER TABLE inventory.items SET SCHEMA catalog")

        # Move auth-related tables back from auth -> public
        tables_auth = ["users", "roles", "permissions", "user_roles", "role_permissions", "token_blocklist", "user_consents"]
        for table in tables_auth:
            op.execute(f"ALTER TABLE auth.{table} SET SCHEMA public")

        op.execute("DROP SCHEMA IF EXISTS auth")
        op.execute("DROP SCHEMA IF EXISTS inventory")
