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
