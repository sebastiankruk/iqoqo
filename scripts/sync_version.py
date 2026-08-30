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
CHANGELOG_PATH = REPO_ROOT / "docs" / "CHANGELOG.md"
MYKG_SCOPE_PATH = REPO_ROOT / ".iqoqo-mykg-scope.yaml"
GRAPHIFYIGNORE_PATH = REPO_ROOT / ".graphifyignore"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_version() -> str:
    """Return the version string from pyproject.toml."""
    with open(PYPROJECT_PATH, "rb") as fh:
        data = tomllib.load(fh)
    return str(data["project"]["version"])


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


def update_changelog(new_version: str) -> None:
    """Ensure a version entry for new_version exists in docs/CHANGELOG.md.

    If the version header `## [{new_version}]` is not present, inserts a template
    for the version at the top of the version list.
    """
    if not CHANGELOG_PATH.exists():
        return
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    if f"## [{new_version}]" in text:
        return

    entry_template = f"## [{new_version}] - TBD\n\n" "### Added\n\n" "### Changed\n\n" "### Fixed\n\n"

    match = re.search(r"(?m)^## \[\d+\.\d+\.\d+\]", text)
    if match:
        idx = match.start()
        updated = text[:idx] + entry_template + text[idx:]
    else:
        updated = text + ("\n\n" if not text.endswith("\n") else "") + entry_template

    CHANGELOG_PATH.write_text(updated, encoding="utf-8")
    try:
        rel_path = CHANGELOG_PATH.relative_to(REPO_ROOT)
    except ValueError:
        rel_path = CHANGELOG_PATH
    print(f"  ✓ {rel_path}")


def update_mykg_scope(old_version: str, new_version: str) -> None:
    """Update the ai-memory version path in .iqoqo-mykg-scope.yaml."""
    if not MYKG_SCOPE_PATH.exists():
        return
    text = MYKG_SCOPE_PATH.read_text(encoding="utf-8")
    old_pattern = f".context/ai-memory/{old_version}"
    new_pattern = f".context/ai-memory/{new_version}"

    if old_pattern in text:
        updated = text.replace(old_pattern, new_pattern)
        MYKG_SCOPE_PATH.write_text(updated, encoding="utf-8")
        print(f"  ✓ {MYKG_SCOPE_PATH.relative_to(REPO_ROOT)} (ai-memory: {old_version} → {new_version})")
    elif new_pattern not in text:
        # If neither old nor new pattern exists, add the new one after the ai-memory comment block
        lines = text.splitlines()
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and "Versioned AI Memory" in line:
                # Insert after the comment block, before the next scope or blank line
                new_lines.append(f"  - {new_pattern}")
                inserted = True
        if inserted:
            MYKG_SCOPE_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"  ✓ {MYKG_SCOPE_PATH.relative_to(REPO_ROOT)} (added ai-memory: {new_version})")


def update_graphifyignore(old_version: str, new_version: str) -> None:
    """Add the old version to .graphifyignore exclusion list.

    The graphify skill auto-detects the current version from package.json,
    so only old versions need to be explicitly excluded.
    """
    if not GRAPHIFYIGNORE_PATH.exists():
        return
    text = GRAPHIFYIGNORE_PATH.read_text(encoding="utf-8")
    old_entry = f".context/ai-memory/{old_version}/"

    if old_entry in text:
        return  # Already excluded

    # Find the ai-memory version exclusion block and add the old version
    pattern = r"(\.context/ai-memory/\d+\.\d+\.\d+/\n)"
    match = re.search(pattern, text)
    if match:
        # Insert after the last version entry in the block
        lines = text.splitlines()
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.startswith(".context/ai-memory/") and line.endswith("/"):
                # Check if next line is still a version entry or something else
                if i + 1 < len(lines) and not lines[i + 1].startswith(".context/ai-memory/"):
                    # This is the last version entry, insert after it
                    new_lines.append(old_entry)
        updated = "\n".join(new_lines) + "\n"
        GRAPHIFYIGNORE_PATH.write_text(updated, encoding="utf-8")
        print(f"  ✓ {GRAPHIFYIGNORE_PATH.relative_to(REPO_ROOT)} (excluded old ai-memory: {old_version})")


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
    update_changelog(new_version)

    if new_version != current:
        print("Syncing knowledge graph configs:")
        update_mykg_scope(current, new_version)
        update_graphifyignore(current, new_version)

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
            "docs/CHANGELOG.md",
            ".iqoqo-mykg-scope.yaml",
            ".graphifyignore",
        ]
        existing_files = [f for f in git_add_files if (REPO_ROOT / f).exists()]
        print(f"  git add {' '.join(existing_files)}")
        print(f"  git commit -m 'chore: bump version to {new_version}'")
        print(f"  git tag v{new_version}")


if __name__ == "__main__":
    main()
