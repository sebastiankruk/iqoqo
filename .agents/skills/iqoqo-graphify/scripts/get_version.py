#!/usr/bin/env python3
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
