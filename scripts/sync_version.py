#!/usr/bin/env python3
"""Sync the project version from pyproject.toml to all package.json files.

Usage:
    python scripts/sync_version.py              # sync current version
    python scripts/sync_version.py --bump patch  # bump patch (0.4.1 -> 0.4.2)
    python scripts/sync_version.py --bump minor  # bump minor (0.4.1 -> 0.5.0)
    python scripts/sync_version.py --bump major  # bump major (0.4.1 -> 1.0.0)
    python scripts/sync_version.py --set 1.2.3   # set explicit version

This script is the single authoritative version-bump tool for iqoqo.
Downstream constants (TypeScript APP_VERSION, Python Config.VERSION, Discogs
User-Agent) are all derived at build / runtime from the files this script
touches, so you never need to edit version strings by hand.
"""

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

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to the repo root, which is the parent of this script)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PACKAGE_JSON_PATHS: list[Path] = [
    REPO_ROOT / "package.json",
    REPO_ROOT / "frontend" / "package.json",
]
PACKAGE_LOCK_JSON_PATHS: list[Path] = [
    REPO_ROOT / "package-lock.json",
    REPO_ROOT / "frontend" / "package-lock.json",
]
TEST_INFRA_CONFIG_PATH = REPO_ROOT / "tests" / "test_infra_config.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_version() -> str:
    """Return the version string from pyproject.toml."""
    with open(PYPROJECT_PATH, "rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' into a 3-tuple of ints."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        print(f"ERROR: '{version}' is not a valid semver string (expected MAJOR.MINOR.PATCH).", file=sys.stderr)
        sys.exit(1)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, part: str) -> str:
    """Return a bumped version string for the given semver component."""
    major, minor, patch = parse_semver(current)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    print(f"ERROR: Unknown bump part '{part}'. Use major, minor, or patch.", file=sys.stderr)
    sys.exit(1)


def write_pyproject_version(new_version: str) -> None:
    """Replace the version field in pyproject.toml in-place."""
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    # Match 'version = "..."' inside [project] section only (first occurrence).
    updated, count = re.subn(
        r'(?m)^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{new_version}\g<2>",
        text,
        count=1,
    )
    if count == 0:
        print("ERROR: Could not locate version field in pyproject.toml.", file=sys.stderr)
        sys.exit(1)
    PYPROJECT_PATH.write_text(updated, encoding="utf-8")
    print(f"  ✓ {PYPROJECT_PATH.relative_to(REPO_ROOT)}")


def write_package_json_version(path: Path, new_version: str) -> None:
    """Update the 'version' field in a package.json file in-place."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = new_version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✓ {path.relative_to(REPO_ROOT)}")


def write_package_lock_json_version(path: Path, new_version: str) -> None:
    """Update the 'version' field in a package-lock.json file in-place."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = new_version
    # Usually also in packages[""]
    if "packages" in data and "" in data["packages"]:
        data["packages"][""]["version"] = new_version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✓ {path.relative_to(REPO_ROOT)}")


def write_test_infra_version(new_version: str) -> None:
    """Update the mock version in test_infra_config.py."""
    if not TEST_INFRA_CONFIG_PATH.exists():
        return
    text = TEST_INFRA_CONFIG_PATH.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        text,
    )
    if count > 0:
        TEST_INFRA_CONFIG_PATH.write_text(updated, encoding="utf-8")
        print(f"  ✓ {TEST_INFRA_CONFIG_PATH.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: parse args, compute new version, write all files."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        metavar="PART",
        help="Bump the given semver component (major | minor | patch).",
    )
    group.add_argument(
        "--set",
        dest="set_version",
        metavar="VERSION",
        help="Set an explicit version string (must be MAJOR.MINOR.PATCH).",
    )
    args = parser.parse_args()

    current = read_version()
    print(f"Current version: {current}")

    if args.bump:
        new_version = bump_version(current, args.bump)
    elif args.set_version:
        parse_semver(args.set_version)  # validate
        new_version = args.set_version
    else:
        # Sync mode: no change to version, just propagate pyproject.toml -> package.json files.
        new_version = current

    if new_version != current:
        print(f"New version:     {new_version}")
    print("Syncing version to:")
    write_pyproject_version(new_version)
    for pkg_path in PACKAGE_JSON_PATHS:
        write_package_json_version(pkg_path, new_version)
    for lock_path in PACKAGE_LOCK_JSON_PATHS:
        if lock_path.exists():
            write_package_lock_json_version(lock_path, new_version)
    write_test_infra_version(new_version)

    print(f"\nDone! Version is now {new_version}.")
    if new_version != current:
        print("Remember to commit all changed files and tag the release:")
        git_add_files = [
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "frontend/package.json",
            "frontend/package-lock.json",
            "tests/test_infra_config.py",
        ]
        existing_files = [f for f in git_add_files if (REPO_ROOT / f).exists()]
        print(f"  git add {' '.join(existing_files)}")
        print(f"  git commit -m 'chore: bump version to {new_version}'")
        print(f"  git tag v{new_version}")


if __name__ == "__main__":
    main()
