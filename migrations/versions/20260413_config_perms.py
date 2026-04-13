# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>
#
"""Add config and user/role management permissions

Revision ID: 20260413_config_perms
Revises: 40408803b0ba
Create Date: 2026-04-13 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "20260413_config_perms"
down_revision = "20260405_fts_video_games"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    conn.execute(
        sa.text("""
            INSERT INTO permissions (name, description)
            VALUES
                ('config:external_apis', 'Manage external API keys and integrations'),
                ('config:federation', 'Manage federation settings'),
                ('config:affiliate', 'Manage affiliate tracking IDs'),
                ('config:internal', 'Manage internal instance settings'),
                ('read:users', 'View users list'),
                ('write:users', 'Modify user roles and active status'),
                ('read:roles', 'View roles list'),
                ('write:roles', 'Create/delete roles and assign permissions')
            ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;
        """)
    )

    conn.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'admin'
            AND p.name IN (
                'config:external_apis',
                'config:federation',
                'config:affiliate',
                'config:internal',
                'read:users',
                'write:users',
                'read:roles',
                'write:roles'
            )
            ON CONFLICT DO NOTHING;
        """)
    )


def downgrade():
    conn = op.get_bind()

    conn.execute(
        sa.text("""
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE name IN (
                    'config:external_apis',
                    'config:federation',
                    'config:affiliate',
                    'config:internal',
                    'read:users',
                    'write:users',
                    'read:roles',
                    'write:roles'
                )
            )
        """)
    )

    conn.execute(
        sa.text("""
            DELETE FROM permissions
            WHERE name IN (
                'config:external_apis',
                'config:federation',
                'config:affiliate',
                'config:internal',
                'read:users',
                'write:users',
                'read:roles',
                'write:roles'
            )
        """)
    )

