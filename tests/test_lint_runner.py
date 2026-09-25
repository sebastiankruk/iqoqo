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
"""Regression checks for canonical CI/local lint commands and AI output mode."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import yaml

from scripts import run_lint

ROOT = Path(__file__).resolve().parent.parent


def test_ai_mode_suppresses_success_output_but_prints_final_status(monkeypatch, capsys) -> None:
    """Routine linter output is quiet only when each check succeeds."""
    monkeypatch.setattr(run_lint, "AI_MODE", True)
    monkeypatch.setattr(run_lint, "CANONICAL_JOBS", [("quiet-job", [("Quiet check", ["quiet-check"], ROOT, True)])])
    monkeypatch.setattr(run_lint, "STRICT_LOCAL_CHECKS", [])

    def succeed(command, **_kwargs):
        """Represent a successful tool that emitted routine diagnostics."""
        return subprocess.CompletedProcess(command, 0, "routine output", "routine warning")

    monkeypatch.setattr(run_lint.subprocess, "run", succeed)

    assert run_lint.main() == 0
    captured = capsys.readouterr()
    assert captured.out == "All canonical lint checks passed.\n"
    assert not captured.err


def test_ai_mode_prints_full_failure_diagnostics(monkeypatch, capsys) -> None:
    """AI output reduction must never hide diagnostics when a check fails."""
    monkeypatch.setattr(run_lint, "AI_MODE", True)
    monkeypatch.setattr(run_lint, "CANONICAL_JOBS", [("broken-job", [("Broken check", ["broken-check"], ROOT, True)])])
    monkeypatch.setattr(run_lint, "STRICT_LOCAL_CHECKS", [])

    def fail(command, **_kwargs):
        """Represent a failed tool with diagnostics on both streams."""
        return subprocess.CompletedProcess(command, 3, "stdout detail", "stderr detail")

    monkeypatch.setattr(run_lint.subprocess, "run", fail)

    assert run_lint.main() == 1
    captured = capsys.readouterr()
    assert "stdout detail" in captured.err
    assert "stderr detail" in captured.err
    assert "Lint failed: 1 blocking check(s)." in captured.err


def test_ai_mode_suppresses_nonblocking_diagnostics_but_counts_them(monkeypatch, capsys) -> None:
    """AI mode suppresses advisory mypy details while retaining final count."""
    monkeypatch.setattr(run_lint, "AI_MODE", True)
    monkeypatch.setattr(
        run_lint,
        "CANONICAL_JOBS",
        [
            (
                "python-job",
                [
                    ("Mypy", ["mypy"], ROOT, False),
                    ("Next blocking check", ["next-check"], ROOT, True),
                ],
            )
        ],
    )
    monkeypatch.setattr(run_lint, "STRICT_LOCAL_CHECKS", [])
    executed = []

    def run_command(command, **_kwargs):
        """Fail mypy softly and let the next canonical check pass."""
        executed.append(command)
        if command == ["mypy"]:
            return subprocess.CompletedProcess(command, 2, "mypy detail", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(run_lint.subprocess, "run", run_command)
    assert run_lint.main() == 0
    assert executed == [["mypy"], ["next-check"]]
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == "Canonical lint passed; 1 check(s) remain non-blocking as in CI.\n"


def test_normal_mode_shows_nonblocking_diagnostics(monkeypatch, capsys) -> None:
    """Advisory diagnostics remain visible outside AI terse mode."""
    monkeypatch.setattr(run_lint, "AI_MODE", False)
    monkeypatch.setattr(run_lint, "CANONICAL_JOBS", [("python-job", [("Mypy", ["mypy"], ROOT, False)])])
    monkeypatch.setattr(run_lint, "STRICT_LOCAL_CHECKS", [])

    def report_mypy_warning(command, **_kwargs):
        """Return advisory diagnostics on both streams."""
        return subprocess.CompletedProcess(command, 2, "mypy stdout", "mypy stderr")

    monkeypatch.setattr(run_lint.subprocess, "run", report_mypy_warning)

    assert run_lint.main() == 0
    captured = capsys.readouterr()
    assert "non-blocking CI warning: Mypy" in captured.out
    assert "mypy stdout" in captured.out
    assert "mypy stderr" in captured.err
    assert "1 check(s) remain non-blocking as in CI." in captured.out


def test_blocking_failure_stops_only_its_ci_job(monkeypatch, capsys) -> None:
    """Fail-fast applies within a CI job while independent lint jobs still run."""
    monkeypatch.setattr(run_lint, "AI_MODE", True)
    monkeypatch.setattr(
        run_lint,
        "CANONICAL_JOBS",
        [
            (
                "python-job",
                [
                    ("First step", ["first"], ROOT, True),
                    ("Skipped step", ["skipped"], ROOT, True),
                ],
            ),
            ("independent-job", [("Independent step", ["independent"], ROOT, True)]),
        ],
    )
    monkeypatch.setattr(run_lint, "STRICT_LOCAL_CHECKS", [])
    executed = []

    def fail_first(command, **_kwargs):
        """Fail one check and allow the independently scheduled check."""
        executed.append(command)
        return subprocess.CompletedProcess(command, 1 if command == ["first"] else 0, "", "failure detail")

    monkeypatch.setattr(run_lint.subprocess, "run", fail_first)
    assert run_lint.main() == 1
    assert executed == [["first"], ["independent"]]
    assert "failure detail" in capsys.readouterr().err


def test_ci_executable_lint_steps_match_local_canonical_map() -> None:
    """Canonical local mapping matches actual CI commands and failure semantics."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8"))
    python_steps = {step.get("name"): step for step in workflow["jobs"]["lint-python"]["steps"]}
    installation_commands = python_steps["Install dependencies"]["run"].splitlines()
    assert installation_commands == [
        "python -m pip install --upgrade pip",
        "pip install black ruff mypy isort",
        "pip install -r requirements.txt",
    ]
    ci_python_commands = [python_steps[name]["run"] for name in ("Run ruff", "Run black", "Run isort", "Run mypy")]
    assert ci_python_commands == [
        "ruff check app/ tests/ scripts/",
        "black --check app/ tests/ scripts/",
        "isort --check-only app/ tests/ scripts/",
        "mypy app/ tests/ scripts/",
    ]
    assert python_steps["Run mypy"]["continue-on-error"] is True
    canonical_python_checks = dict(run_lint.CANONICAL_JOBS)["lint-python"]
    assert [check[1][1:] for check in canonical_python_checks[:3]] == [
        ["-m", "pip", "install", "--upgrade", "pip"],
        ["-m", "pip", "install", "black", "ruff", "mypy", "isort"],
        ["-m", "pip", "install", "-r", "requirements.txt"],
    ]
    assert [check[1][1:] for check in canonical_python_checks[3:]] == [
        ["check", "app/", "tests/", "scripts/"],
        ["--check", "app/", "tests/", "scripts/"],
        ["--check-only", "app/", "tests/", "scripts/"],
        ["app/", "tests/", "scripts/"],
    ]
    assert [check[3] for check in canonical_python_checks] == [True, True, True, True, True, True, False]

    javascript_steps = workflow["jobs"]["lint-javascript"]["steps"]
    javascript_commands = [step.get("run", "").strip() for step in javascript_steps if step.get("run")]
    assert javascript_commands == ["npm install -g eslint prettier stylelint stylelint-config-standard"]
    javascript_local_checks = dict(run_lint.CANONICAL_JOBS)["lint-javascript"]
    assert [shlex.join(check[1]) for check in javascript_local_checks] == javascript_commands
    assert all("ESLint" not in check[0] for checks in dict(run_lint.CANONICAL_JOBS).values() for check in checks)

    markdown_steps = workflow["jobs"]["lint-markdown"]["steps"]
    markdown_command = next(step["run"] for step in markdown_steps if step.get("name") == "Run Markdownlint")
    local_markdown_check = next(check for check in dict(run_lint.CANONICAL_JOBS)["lint-markdown"] if check[0] == "Markdownlint")
    assert local_markdown_check[1] == shlex.split(markdown_command)
    all_checks = [check for checks in dict(run_lint.CANONICAL_JOBS).values() for check in checks]
    assert "./scripts/check_license.sh" in [check[1][0] for check in all_checks]


def test_python_lint_tools_use_the_same_unpinned_install_semantics_as_ci() -> None:
    """Local setup reproduces CI's latest-compatible package installation."""
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "black==" not in requirements
    assert "ruff==" not in requirements
    assert "isort==" not in requirements
    assert "mypy==" not in requirements
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/run_lint.py\n" in makefile
    assert "scripts/run_lint.py --all" in makefile
