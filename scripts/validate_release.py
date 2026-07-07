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
"""Validate release branch version consistency.

Checks that:
  1. pyproject.toml version matches the expected release version
  2. package.json and frontend/package.json versions match
  3. docs/CHANGELOG.md has an entry for the expected version

Usage:
    python scripts/validate_release.py <version>
    python scripts/validate_release.py

When run without arguments, extracts version from the branch name
(expects git ref name like ``release/0.7.7``).
"""

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def die(*msgs: str) -> None:
    for m in msgs:
        print(f"FAIL: {m}", file=sys.stderr)
    sys.exit(1)


def get_version_from_branch() -> str:
    ref = (
        Path(REPO_ROOT / ".git" / "HEAD").read_text().strip()
        if (REPO_ROOT / ".git" / "HEAD").exists()
        else ""
    )
    match = re.search(r"release/(\d+\.\d+\.\d+)", ref)
    if not match:
        die("Cannot extract version from branch name (expected refs/heads/release/X.Y.Z)")
    return match.group(1)


def read_pyproject_version() -> str:
    with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def read_package_json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["version"]


def check_changelog_entry(version: str) -> None:
    changelog = REPO_ROOT / "docs" / "CHANGELOG.md"
    if not changelog.exists():
        die(f"{changelog} not found")

    text = changelog.read_text(encoding="utf-8")
    if f"## [{version}]" not in text:
        die(f"docs/CHANGELOG.md has no entry for version [{version}]")


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else get_version_from_branch()

    errors = []

    pyproject_version = read_pyproject_version()
    if pyproject_version != version:
        errors.append(f"pyproject.toml has version '{pyproject_version}', expected '{version}'")

    for pkg_path in [REPO_ROOT / "package.json", REPO_ROOT / "frontend" / "package.json"]:
        if not pkg_path.exists():
            continue
        pkg_version = read_package_json_version(pkg_path)
        if pkg_version != version:
            errors.append(f"{pkg_path.relative_to(REPO_ROOT)} has version '{pkg_version}', expected '{version}'")

    check_changelog_entry(version)

    if errors:
        die(*errors)

    print(f"OK: all version files and CHANGELOG are consistent at {version}")


if __name__ == "__main__":
    main()
