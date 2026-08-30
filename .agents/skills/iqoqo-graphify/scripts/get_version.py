#!/usr/bin/env python3
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
"""Read current iqoqo version from package.json or pyproject.toml."""

import json
import re
from pathlib import Path


def get_version(project_root: Path = None) -> str:
    """Read version from package.json or pyproject.toml."""
    if project_root is None:
        project_root = Path.cwd()
    
    # Try package.json first
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            version = data.get("version")
            if version:
                return version
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Fallback to pyproject.toml
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
        except (OSError, re.error):
            pass
    
    return "unknown"


def main():
    version = get_version()
    print(version)


if __name__ == "__main__":
    main()
