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
import json
import tomllib
from pathlib import Path


def test_versions_are_in_sync() -> None:
    """
    Ensure that the version in pyproject.toml matches the version in both package.json files.
    """
    root_dir = Path(__file__).parents[1]

    # Read pyproject.toml
    with open(root_dir / "pyproject.toml", "rb") as f:
        pyproject_data = tomllib.load(f)
        py_version = pyproject_data["project"]["version"]

    # Read package.json (root)
    with open(root_dir / "package.json", encoding="utf-8") as f:
        root_package_data = json.load(f)
        root_js_version = root_package_data["version"]

    assert py_version == root_js_version, f"Version mismatch: pyproject.toml has {py_version}, but root package.json has {root_js_version}."

    # Read package.json (frontend)
    with open(root_dir / "frontend" / "package.json", encoding="utf-8") as f:
        frontend_package_data = json.load(f)
        frontend_js_version = frontend_package_data["version"]

    assert (
        py_version == frontend_js_version
    ), f"Version mismatch: pyproject.toml has {py_version}, but frontend/package.json has {frontend_js_version}."
