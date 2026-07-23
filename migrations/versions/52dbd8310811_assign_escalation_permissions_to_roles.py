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

"""Assign escalation permissions to roles.

Revision ID: 52dbd8310811
Revises: 20260722_add_escalation_requests
Create Date: 2026-07-23 15:34:11.425193

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "52dbd8310811"
down_revision = "20260722_add_escalation_requests"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Insert escalate:request permission for the user role
    conn.execute(
        sa.text("""
            INSERT INTO auth.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM auth.roles r, auth.permissions p
            WHERE r.name = 'user'
              AND p.name = 'escalate:request'
            ON CONFLICT (role_id, permission_id) DO NOTHING
        """)
    )

    # Insert escalate:resolve permission for the custodian role
    conn.execute(
        sa.text("""
            INSERT INTO auth.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM auth.roles r, auth.permissions p
            WHERE r.name = 'custodian'
              AND p.name = 'escalate:resolve'
            ON CONFLICT (role_id, permission_id) DO NOTHING
        """)
    )

    # Insert escalate:resolve permission for the admin role
    conn.execute(
        sa.text("""
            INSERT INTO auth.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM auth.roles r, auth.permissions p
            WHERE r.name = 'admin'
              AND p.name = 'escalate:resolve'
            ON CONFLICT (role_id, permission_id) DO NOTHING
        """)
    )


def downgrade():
    conn = op.get_bind()

    # Remove escalate:request from user role
    conn.execute(
        sa.text("""
            DELETE FROM auth.role_permissions
            WHERE role_id = (SELECT id FROM auth.roles WHERE name = 'user')
              AND permission_id = (SELECT id FROM auth.permissions WHERE name = 'escalate:request')
        """)
    )

    # Remove escalate:resolve from custodian role
    conn.execute(
        sa.text("""
            DELETE FROM auth.role_permissions
            WHERE role_id = (SELECT id FROM auth.roles WHERE name = 'custodian')
              AND permission_id = (SELECT id FROM auth.permissions WHERE name = 'escalate:resolve')
        """)
    )

    # Remove escalate:resolve from admin role
    conn.execute(
        sa.text("""
            DELETE FROM auth.role_permissions
            WHERE role_id = (SELECT id FROM auth.roles WHERE name = 'admin')
              AND permission_id = (SELECT id FROM auth.permissions WHERE name = 'escalate:resolve')
        """)
    )
