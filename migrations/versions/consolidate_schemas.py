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

"""Consolidate schemas: move settings to catalog, telemetry to inventory, drop stale public tables

Revision ID: consolidate_schemas
Revises: drop_stale_public_tables
Create Date: 2026-04-14 09:05:00.000000

This migration completes the schema consolidation:
- Moves instance_settings from public to catalog schema
- Moves llm_telemetry from public to inventory schema
- Drops stale duplicate tables in public schema

"""

from alembic import op
from sqlalchemy import inspect


# revision identifiers
revision = "consolidate_schemas"
down_revision = "drop_stale_public_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move tables to proper schemas and drop stale duplicates."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Step 1: Move instance_settings to catalog schema
    if inspector.has_table("instance_settings", schema="public"):
        op.execute("""
            CREATE TABLE IF NOT EXISTS catalog.instance_settings (LIKE public.instance_settings INCLUDING ALL)
        """)
        op.execute("""
            INSERT INTO catalog.instance_settings 
            SELECT * FROM public.instance_settings
            ON CONFLICT DO NOTHING
        """)
        op.execute("DROP TABLE IF EXISTS public.instance_settings CASCADE")
    
    # Step 2: Move llm_telemetry to inventory schema
    if inspector.has_table("llm_telemetry", schema="public"):
        op.execute("""
            CREATE TABLE IF NOT EXISTS inventory.llm_telemetry (LIKE public.llm_telemetry INCLUDING ALL)
        """)
        op.execute("""
            INSERT INTO inventory.llm_telemetry 
            SELECT * FROM public.llm_telemetry
            ON CONFLICT DO NOTHING
        """)
        op.execute("DROP TABLE IF EXISTS public.llm_telemetry CASCADE")
    
    # Step 3: Drop stale public.token_blocklist
    op.execute("DROP TABLE IF EXISTS public.token_blocklist CASCADE")
    
    # Step 4: Drop empty FRBR duplicate tables in public schema
    stale_frbr_tables = [
        "works", "expressions", "manifestations", "contributors",
        "work_contributions", "expression_contributions",
        "manifestation_contributions", "work_parts", "container_aggregations",
    ]
    
    for table in stale_frbr_tables:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")


def downgrade() -> None:
    """Rollback: move tables back to public schema (not typically needed)."""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Move instance_settings back to public
    if inspector.has_table("instance_settings", schema="catalog"):
        op.execute("""
            CREATE TABLE IF NOT EXISTS public.instance_settings (LIKE catalog.instance_settings INCLUDING ALL)
        """)
        op.execute("""
            INSERT INTO public.instance_settings 
            SELECT * FROM catalog.instance_settings
            ON CONFLICT DO NOTHING
        """)
        op.execute("DROP TABLE IF EXISTS catalog.instance_settings CASCADE")
    
    # Move llm_telemetry back to public
    if inspector.has_table("llm_telemetry", schema="inventory"):
        op.execute("""
            CREATE TABLE IF NOT EXISTS public.llm_telemetry (LIKE inventory.llm_telemetry INCLUDING ALL)
        """)
        op.execute("""
            INSERT INTO public.llm_telemetry 
            SELECT * FROM inventory.llm_telemetry
            ON CONFLICT DO NOTHING
        """)
        op.execute("DROP TABLE IF EXISTS inventory.llm_telemetry CASCADE")
