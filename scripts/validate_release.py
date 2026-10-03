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
  4. docs/RELEASE_PROCESS.md quotes the same container image size figures as the
     enforced budget in deploy/image-size-budget.txt

Usage:
    python scripts/validate_release.py <version>
    python scripts/validate_release.py
    python scripts/validate_release.py --image-size-only

When run without arguments, extracts version from the branch name
(expects git ref name like ``release/0.7.7``). ``--image-size-only`` runs just
the container image size reference check, which needs no release branch.
"""

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
BUDGET_FILE = REPO_ROOT / "deploy" / "image-size-budget.txt"
RELEASE_PROCESS = REPO_ROOT / "docs" / "RELEASE_PROCESS.md"


def read_image_size_budget() -> dict[str, int]:
    """Parse the enforced image size budget.

    Deliberately re-parses the file rather than importing scripts/check_image_size.py:
    this job runs before any dependency is installed, and the release plan quoting a
    different number than the build gate is exactly the drift this catches.
    """
    if not BUDGET_FILE.exists():
        die(f"{BUDGET_FILE} not found; the image size gate has no budget to enforce")

    budget: dict[str, int] = {}
    for line in BUDGET_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() in ("MAX_BYTES", "MEASURED_BYTES"):
            budget[key.strip()] = int(value.strip())

    for key in ("MAX_BYTES", "MEASURED_BYTES"):
        if key not in budget:
            die(f"{BUDGET_FILE} does not define {key}")
    if budget["MEASURED_BYTES"] > budget["MAX_BYTES"]:
        die(f"{BUDGET_FILE} records a measurement ({budget['MEASURED_BYTES']}) above its own budget ({budget['MAX_BYTES']})")
    return budget


def check_image_size_reference() -> None:
    """Require the release plan to quote the budget file's own numbers.

    The previous size target was "<500 MB" in prose, unmet for a whole release
    because prose cannot fail. Replacing it with an enforced budget only helps if
    the human-facing release plan quotes that budget rather than a remembered
    approximation, so a stale figure here is a release blocker.
    """
    budget = read_image_size_budget()
    if not RELEASE_PROCESS.exists():
        die(f"{RELEASE_PROCESS} not found")

    text = RELEASE_PROCESS.read_text(encoding="utf-8")
    for key, value in (("MAX_BYTES", budget["MAX_BYTES"]), ("MEASURED_BYTES", budget["MEASURED_BYTES"])):
        if str(value) not in text:
            die(
                f"{RELEASE_PROCESS.relative_to(REPO_ROOT)} does not quote {key}={value} from "
                f"{BUDGET_FILE.relative_to(REPO_ROOT)}; update both in the same commit"
            )


def die(*msgs: str) -> NoReturn:
    """Print each message to stderr and exit non-zero."""
    for m in msgs:
        print(f"FAIL: {m}", file=sys.stderr)
    sys.exit(1)


def get_version_from_branch() -> str:
    """Read the release version from the branch name.

    The branch is the source of truth for what is about to ship, so a mismatch with
    the packaging metadata is a release blocker rather than a warning."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
        )
        ref = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        ref = ""

    match = re.search(r"(?:release|hotfix)/(\d+\.\d+\.\d+)", ref)
    if not match:
        die("Cannot extract version from branch name (expected release/X.Y.Z or hotfix/X.Y.Z)")
    return match.group(1)


def read_pyproject_version() -> str:
    """Read the version declared in pyproject.toml."""
    with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    return str(data["project"]["version"])


def read_package_json_version(path: Path) -> str:
    """Read the version declared in a package.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data["version"])


def check_changelog_entry(version: str) -> None:
    """Require a changelog section for *version*.

    A release without a changelog entry ships undocumented changes, so this fails
    rather than warns."""
    changelog = REPO_ROOT / "docs" / "CHANGELOG.md"
    if not changelog.exists():
        die(f"{changelog} not found")

    text = changelog.read_text(encoding="utf-8")
    if f"## [{version}]" not in text:
        die(f"docs/CHANGELOG.md has no entry for version [{version}]")


def main() -> None:
    """Run every pre-release consistency check."""
    # Lets the image-size reference be checked on any branch, where there is no
    # release version to validate the rest against.
    if "--image-size-only" in sys.argv[1:]:
        check_image_size_reference()
        budget = read_image_size_budget()
        print(
            f"OK: image size budget {budget['MAX_BYTES']} bytes is quoted in the release plan "
            f"(measured {budget['MEASURED_BYTES']} bytes)"
        )
        return

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
    check_image_size_reference()

    if errors:
        die(*errors)

    print(f"OK: all version files and CHANGELOG are consistent at {version}")
    budget = read_image_size_budget()
    print(
        f"OK: image size budget {budget['MAX_BYTES']} bytes is quoted in the release plan " f"(measured {budget['MEASURED_BYTES']} bytes)"
    )


if __name__ == "__main__":
    main()
