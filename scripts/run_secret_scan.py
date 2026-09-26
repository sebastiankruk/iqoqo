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
"""Local secret scanner runner wrapping Gitleaks (CLI or Docker fallback)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / ".gitleaks.toml"


def resolve_gitleaks_cmd() -> list[str] | None:
    """Find native gitleaks binary or construct Docker fallback command."""
    # Check standard PATH or user local bin
    local_bin_gitleaks = Path.home() / ".local" / "bin" / "gitleaks"
    if shutil.which("gitleaks"):
        return ["gitleaks"]
    if local_bin_gitleaks.exists() and os.access(local_bin_gitleaks, os.X_OK):
        return [str(local_bin_gitleaks)]

    # Fallback to docker if available
    if shutil.which("docker"):
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{ROOT}:/path",
            "-w",
            "/path",
            "zricethezav/gitleaks:latest",
        ]

    return None


def get_base_branch() -> str | None:
    """Detect reference branch for diff scanning (e.g., origin/main or origin/master)."""
    for candidate in ("origin/main", "origin/master", "main", "master"):
        check = subprocess.run(
            ["git", "rev-parse", "--verify", candidate],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if check.returncode == 0:
            return candidate
    return None


def run_scan(verbose: bool = False) -> int:
    """Execute Gitleaks protect (working tree) and detect (branch commits)."""
    base_cmd = resolve_gitleaks_cmd()
    if not base_cmd:
        print(
            "⚠️  Gitleaks not installed and Docker not available. Skipping secret scan.",
            file=sys.stderr,
        )
        return 0

    common_flags: list[str] = []
    if CONFIG_PATH.exists():
        common_flags.extend(["--config", str(CONFIG_PATH)])
    if verbose:
        common_flags.append("--verbose")

    # 1. Protect scan (uncommitted changes)
    protect_cmd = [*base_cmd, "protect", *common_flags]
    res = subprocess.run(protect_cmd, cwd=ROOT, check=False)
    if res.returncode != 0:
        print("❌ Gitleaks detected secrets in uncommitted changes!", file=sys.stderr)
        return res.returncode

    # 2. Detect scan on branch commits against origin/main if git repo
    base_branch = get_base_branch()
    if base_branch:
        detect_cmd = [
            *base_cmd,
            "detect",
            f"--log-opts={base_branch}..HEAD",
            *common_flags,
        ]
        res = subprocess.run(detect_cmd, cwd=ROOT, check=False)
        if res.returncode != 0:
            print(
                f"❌ Gitleaks detected secrets in commits between {base_branch} and HEAD!",
                file=sys.stderr,
            )
            return res.returncode

    if not os.environ.get("IQOQO_AI_MODE"):
        print("✅ Gitleaks secret scan passed: 0 leaks found.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Gitleaks secret scan.")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose Gitleaks output.",
    )
    args = parser.parse_args()
    return run_scan(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
