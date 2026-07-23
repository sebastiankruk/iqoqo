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
import pytest

from app.db.models import Permission, Role
from scripts.init_auth import run_init_auth


def test_init_auth_roles_permissions(app):
    """Test that init_auth properly assigns permissions to admin and contributor roles."""
    run_init_auth(app)

    with app.app_context():
        # 1. Verify admin has all permissions
        admin_role = Role.query.filter_by(name="admin").first()
        assert admin_role is not None, "Admin role should be created"

        all_perms = {p.name for p in Permission.query.all()}
        admin_perms = {p.name for p in admin_role.permissions}

        assert admin_perms == all_perms, "Admin must be assigned all system permissions"

        # 2. Verify contributor has correct specific selected permissions
        contributor_role = Role.query.filter_by(name="contributor").first()
        assert contributor_role is not None, "Contributor role should be created"

        contributor_perms = {p.name for p in contributor_role.permissions}

        # Determine expected contributor permissions dynamically based on the wildcard rules
        # Contributor gets: all :metadata, edit:cover (full editor + upload), llm_generate:*, delete:item, escalate:resolve
        expected_perms = {
            p
            for p in all_perms
            if (p.endswith(":metadata") or p == "edit:cover" or p.startswith("llm_generate:") or p == "delete:item" or p == "escalate:resolve")
        }

        missing = expected_perms - contributor_perms
        extra = contributor_perms - expected_perms

        assert not missing, f"Contributor is missing expected permissions: {missing}"
        assert not extra, f"Contributor has unexpected permissions: {extra}"
        assert contributor_perms == expected_perms

        # 3. Verify standard user has correct permissions
        user_role = Role.query.filter_by(name="user").first()
        assert user_role is not None, "User role should be created"

        user_perms = {p.name for p in user_role.permissions}
        expected_user_perms = {
            "write:item",
            "update:item",
            "delete:item",
            "read:metadata",
            "upload:cover",
            "refetch:cover",
            "regenerate:cover",
            "llm_generate:metadata",
            "llm_generate:cover",
            "escalate:request",
        }

        missing_user = expected_user_perms - user_perms
        extra_user = user_perms - expected_user_perms

        assert not missing_user, f"User is missing expected permissions: {missing_user}"
        assert not extra_user, f"User has unexpected permissions: {extra_user}"
        assert user_perms == expected_user_perms
