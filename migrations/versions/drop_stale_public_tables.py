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

"""Drop stale public schema tables (duplicate of auth/inventory schemas)

Revision ID: drop_stale_public_tables
Revises: 20260413_config_perms
Create Date: 2026-04-14 07:50:00.000000

These tables were created when DATABASE_URL wasn't set to PostgreSQL.
They are now superseded by schema-qualified tables:
- auth.users, auth.permissions, auth.roles, etc.
- inventory.items
- catalog.works, catalog.manifestations, etc.

"""

from alembic import op


# revision identifiers
revision = "drop_stale_public_tables"
down_revision = "20260413_config_perms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop stale public schema tables that duplicate schema-qualified tables."""
    # Order matters: drop tables with foreign key dependencies first
    # CASCADE drops dependent views/constraints automatically
    
    # These reference public.users
    op.execute("DROP TABLE IF EXISTS public.user_consents CASCADE")
    op.execute("DROP TABLE IF EXISTS public.items CASCADE")  # may already be empty
    
    # Auth tables (these were stale, now fixed)
    op.execute("DROP TABLE IF EXISTS public.user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS public.role_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS public.permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS public.roles CASCADE")
    op.execute("DROP TABLE IF EXISTS public.users CASCADE")
    
    # These are separate - not duplicates but in public schema
    # Keeping them as they're part of the working set
    # public.alembic_version, public.instance_settings, etc.


def downgrade() -> None:
    """Recreate public schema tables (not typically needed)."""
    pass
