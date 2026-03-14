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
import re

from app.core import permissions as perms


def test_permissions_yaml_matches_enum():
    with open("shared/permissions.yaml", encoding="utf-8") as f:
        text = f.read()
    # Naive extraction to avoid PyYAML as a test dependency in CI
    names = set(re.findall(r"^\s*-\s+name:\s*(\S+)$", text, flags=re.M))
    enum_values = {m.value for m in perms.ItemPermissions}
    assert names.issubset(enum_values)
    assert enum_values.issubset(names)
