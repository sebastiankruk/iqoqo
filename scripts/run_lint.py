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
"""Run the one canonical lint suite used by both local Make and GitHub Actions."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = Path(sys.executable).parent
AI_MODE = os.environ.get("IQOQO_AI_MODE") == "1"


def tool(name: str) -> str:
    """Resolve Python tools from the current interpreter's environment."""
    candidate = VENV_BIN / name
    return str(candidate) if candidate.exists() else name


Check = tuple[str, list[str], Path, bool]
CANONICAL_JOBS: list[tuple[str, list[Check]]] = [
    (
        "lint-python",
        [
            (
                "Upgrade pip",
                [tool("python"), "-m", "pip", "install", "--upgrade", "pip"],
                ROOT,
                True,
            ),
            (
                "Install Python lint tools",
                [tool("python"), "-m", "pip", "install", "black", "ruff", "mypy", "isort"],
                ROOT,
                True,
            ),
            (
                "Install requirements",
                [tool("python"), "-m", "pip", "install", "-r", "requirements.txt"],
                ROOT,
                True,
            ),
            ("Ruff", [tool("ruff"), "check", "app/", "tests/", "scripts/"], ROOT, True),
            ("Black", [tool("black"), "--check", "app/", "tests/", "scripts/"], ROOT, True),
            ("isort", [tool("isort"), "--check-only", "app/", "tests/", "scripts/"], ROOT, True),
            # This is continue-on-error in the pre-existing CI workflow.
            ("Mypy (non-blocking, matching CI continue-on-error)", [tool("mypy"), "app/", "tests/", "scripts/"], ROOT, False),
        ],
    ),
    (
        "lint-javascript",
        [
            (
                "Install JavaScript lint tools (CI install-only job)",
                ["npm", "install", "-g", "eslint", "prettier", "stylelint", "stylelint-config-standard"],
                ROOT,
                True,
            )
        ],
    ),
    (
        "lint-markdown",
        [
            ("Install Markdownlint", ["npm", "install", "-g", "markdownlint-cli2"], ROOT, True),
            (
                "Markdownlint",
                [
                    "markdownlint-cli2",
                    "**/*.md",
                    "!node_modules",
                    "!.venv",
                    "!frontend/node_modules",
                    "!frontend/.next",
                    "!.github",
                    "!.pytest_cache",
                    "!.agent",
                    "!.agents",
                    "!.gemini",
                    "!.caim",
                    "!frontend/playwright-report",
                    "!frontend/test-results",
                    "!graphify-out",
                    "!mykg_sessions",
                    "!.context",
                    "!openspec/changes",
                ],
                ROOT,
                True,
            ),
        ],
    ),
    ("lint-license", [("License headers", ["./scripts/check_license.sh"], ROOT, True)]),
    ("secret-scan", [("Secret scanning", [tool("python"), "scripts/run_secret_scan.py"], ROOT, True)]),
]

STRICT_LOCAL_CHECKS: list[tuple[str, list[str], Path, bool]] = [
    ("Pylint (local-only)", [tool("pylint"), "app/", "tests/", "scripts/"], ROOT, True),
    ("ESLint (local-only)", ["npm", "run", "lint"], ROOT / "frontend", True),
    ("TypeScript (local-only)", ["npx", "tsc", "--noEmit"], ROOT / "frontend", True),
    (
        "Stylelint (local-only)",
        ["npx", "stylelint", "--allow-empty-input", "frontend/app/**/*.css", "frontend/components/**/*.css"],
        ROOT,
        True,
    ),
    ("YAML configuration (local-only)", [tool("python"), "scripts/validate_yaml.py"], ROOT, True),
]


def run_jobs(jobs: list[tuple[str, list[Check]]]) -> tuple[int, int]:
    """Run independent CI jobs and stop each job at its first blocking step error."""
    blocking_failures = 0
    nonblocking_failures = 0
    for job_name, checks in jobs:
        for label, command, cwd, blocking in checks:
            if not AI_MODE:
                print(f"==> {job_name}: {label}: {shlex.join(command)}", flush=True)
            try:
                result = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
            except OSError as error:
                result = subprocess.CompletedProcess(command, 127, "", str(error))

            if result.returncode != 0:
                if blocking:
                    print(f"LINT failed: {label} (exit {result.returncode}): {shlex.join(command)}", file=sys.stderr)
                    if result.stdout:
                        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", file=sys.stderr)
                    if result.stderr:
                        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
                    blocking_failures += 1
                    break
                nonblocking_failures += 1
                if not AI_MODE:
                    print(f"LINT reported a non-blocking CI warning: {label} (exit {result.returncode})")
                    if result.stdout:
                        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
                    if result.stderr:
                        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
            elif not AI_MODE:
                if result.stdout:
                    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
                if result.stderr:
                    print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)

    return blocking_failures, nonblocking_failures


def main(include_strict: bool = False) -> int:
    """Run the executable CI baseline, optionally followed by local-only checks."""
    jobs = list(CANONICAL_JOBS)
    if include_strict:
        jobs.append(("lint-all-local", STRICT_LOCAL_CHECKS))
    blocking_failures, nonblocking_failures = run_jobs(jobs)
    if blocking_failures:
        print(f"Lint failed: {blocking_failures} blocking check(s).", file=sys.stderr)
        return 1
    if nonblocking_failures:
        print(f"Canonical lint passed; {nonblocking_failures} check(s) remain non-blocking as in CI.")
        return 0
    print("All canonical lint checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(include_strict="--all" in sys.argv[1:]))
