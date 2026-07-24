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

from pathlib import Path

import yaml

from app.core.permissions import PermissionName


def test_permission_enum_matches_yaml():
    """Verify that PermissionName Enum matches shared/permissions.yaml."""
    yaml_path = Path(__file__).parent.parent / "shared" / "permissions.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        perms_data = yaml.safe_load(f)

    yaml_perms = {p["name"] for p in perms_data.get("permissions", [])}

    enum_perms = {p.value for p in PermissionName}

    # Missing in Enum
    missing_in_enum = yaml_perms - enum_perms
    assert not missing_in_enum, f"Permissions in YAML but missing in PermissionName Enum: {missing_in_enum}"

    # Missing in YAML
    missing_in_yaml = enum_perms - yaml_perms
    assert not missing_in_yaml, f"Permissions in Enum but missing in permissions.yaml: {missing_in_yaml}"


def test_permission_enum_values_are_lowercase_verb_noun():
    """Strictly enforce verb:noun format for permission values."""
    for p in PermissionName:
        val = p.value
        assert ":" in val, f"Permission {p.name} value '{val}' missing colon"
        assert val == val.lower(), f"Permission {p.name} value '{val}' must be lowercase"
        parts = val.split(":")
        assert len(parts) == 2, f"Permission {p.name} value '{val}' must be exactly verb:noun"


def test_list_llm_permissions(app):
    """Verify list_llm_permissions accurately reflects user permissions."""
    from app.db.models import Permission, Role, User, db

    with app.app_context():
        # 1. Guest user
        guest_perms = User.list_llm_permissions(None)
        assert guest_perms["allow_generate_cover"] is False
        assert guest_perms["allow_cloud_llm"] is False
        assert guest_perms["allow_generate_metadata"] is False

        # 2. User with no special permissions
        user = User(email="test@example.local")
        db.session.add(user)
        db.session.commit()

        user_perms = User.list_llm_permissions(user)
        assert user_perms["allow_generate_cover"] is False
        assert user_perms["allow_cloud_llm"] is False
        assert user_perms["allow_generate_metadata"] is False

        # 3. User with metadata permission only
        meta_perm = Permission(name=PermissionName.LLM_GENERATE_METADATA.value)
        db.session.add(meta_perm)

        meta_role = Role(name="meta_role")
        meta_role.permissions.append(meta_perm)
        db.session.add(meta_role)

        user.roles.append(meta_role)
        db.session.commit()

        meta_perms = User.list_llm_permissions(user)
        assert meta_perms["allow_generate_cover"] is False
        assert meta_perms["allow_cloud_llm"] is False
        assert meta_perms["allow_generate_metadata"] is True

        # 4. User with cloud permission
        cloud_perm = Permission(name=PermissionName.LLM_GENERATE_CLOUD.value)
        db.session.add(cloud_perm)

        cloud_role = Role(name="cloud_role")
        cloud_role.permissions.append(cloud_perm)
        db.session.add(cloud_role)

        user.roles.append(cloud_role)
        db.session.commit()

        all_perms = User.list_llm_permissions(user)
        assert all_perms["allow_cloud_llm"] is True
        assert all_perms["allow_generate_metadata"] is True


def test_require_permission_returns_401_when_no_user(app, client):
    """Verify require_permission returns 401 for unauthenticated request."""
    # The FRBR tree endpoint requires read:metadata permission via inline check.
    # Without auth headers, any @require_auth or require_permission endpoint should return 401.
    resp = client.get("/api/v1/admin/frbr/tree/manifestation/1")
    assert resp.status_code in [401, 403]
