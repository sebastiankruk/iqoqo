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
"""Tests for AiOps terse mode across pytest, Makefile targets, BATS formatter, and frontend runners."""

import io
import os
import pathlib
import re
import subprocess
import sys
from unittest.mock import MagicMock

import pytest
from conftest import pytest_configure

from scripts import format_bats_ai, run_tests_parallel

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_pytest_configure_ai_mode_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pytest_configure modifies options when IQOQO_AI_MODE is set."""
    monkeypatch.setenv("IQOQO_AI_MODE", "1")
    config = MagicMock()
    config.option = MagicMock()
    config.option.plugins = []

    pytest_configure(config)

    assert config.option.verbose == -1
    assert config.option.tbstyle == "short"
    assert config.option.no_header is True
    assert "no:sugar" in config.option.plugins
    config.pluginmanager.set_blocked.assert_called_with("sugar")


def test_pytest_configure_ai_mode_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pytest_configure leaves options unchanged when IQOQO_AI_MODE is unset."""
    monkeypatch.delenv("IQOQO_AI_MODE", raising=False)
    config = MagicMock()
    config.option = MagicMock()
    config.option.verbose = 0
    config.option.tbstyle = "auto"
    config.option.no_header = False
    config.option.plugins = []

    pytest_configure(config)

    assert config.option.verbose == 0
    assert config.option.tbstyle == "auto"
    assert config.option.no_header is False
    assert "no:sugar" not in config.option.plugins
    config.pluginmanager.set_blocked.assert_not_called()


def test_format_bats_ai_passes_with_dots(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Assert format_bats_ai emits one dot per passing TAP line and concise summary."""
    tap = "1..3\nok 1 - first test\nok 2 - second test\nok 3 - third test\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(tap))

    rc = format_bats_ai.main()
    captured = capsys.readouterr()

    assert rc == 0
    assert captured.out == "...\nBATS: 3 tests passed.\n"


def test_format_bats_ai_fails_with_details(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Assert format_bats_ai emits F and prints diagnostic failure details on failure."""
    tap = "1..2\nok 1 - passes\nnot ok 2 - fails\n# (in test file foo.bats, line 12)\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(tap))

    rc = format_bats_ai.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert captured.out.startswith(".F\n")
    assert "BATS FAILURES:" in captured.out
    assert "not ok 2 - fails" in captured.out
    assert "FAILED (1 failed, 1 passed)" in captured.out


def test_format_bats_ai_malformed_input_returns_nonzero(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Assert format_bats_ai prints raw error lines and exits 1 when no TAP assertions match."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("bats: syntax error\n"))

    rc = format_bats_ai.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "bats: syntax error" in captured.out


def test_run_tests_parallel_ai_mode_flags_and_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert run_tests_parallel discovers subdir tests and sets terse flags in AI_MODE."""
    discovered = run_tests_parallel.get_all_test_files()
    assert "tests/core/test_telemetry.py" in discovered
    assert "tests/integration/api/test_llm_guards.py" in discovered
    assert "tests/scripts/test_iqoqo_installer.py" in discovered

    domain, api, tooling = run_tests_parallel.partition_backend_tests()
    combined = domain + api + tooling
    assert len(combined) == len(set(combined)) == len(discovered)

    monkeypatch.setattr(run_tests_parallel, "AI_MODE", True)
    streams = run_tests_parallel.build_stream_definitions()
    assert streams["domain"]["commands"][0][1:4] == ["-q", "--tb=short", "--no-header"]
    assert streams["frontend"]["commands"][0][-2:] == ["--", "--reporter=dot"]
    tooling_cmds = " ".join(" ".join(cmd) for cmd in streams["tooling"]["commands"])
    if "bats" in tooling_cmds:
        assert "format_bats_ai.py" in tooling_cmds


def test_makefile_test_targets_honor_ai_mode_and_dry_run_safety() -> None:
    """Verify Makefile test targets avoid hardcoded -v, suppress banners, and stay safe under make -n."""
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    # No bare -v passed to pytest in test-* recipes
    assert ".venv/bin/pytest tests/integration/db/ -v" not in makefile_text
    assert "tests/scripts/" in makefile_text
    assert "help_hub_workflow.spec.ts" not in makefile_text

    # No bare $(MAKE) inside multi-line shell recipes that would execute under make -n
    for target in ("test-e2e-federation:", "test-merge-integrity-pg:"):
        block = makefile_text.split(target, 1)[1].split("\n\n", 1)[0]
        assert "$(MAKE)" not in block, f"{target} must not embed $(MAKE) in a multi-line shell block"

    # Confirm test-backend-pg and test-e2e-federation gate echoes on IQOQO_AI_MODE
    pg_block = makefile_text.split("test-backend-pg:", 1)[1].split("\n\n", 1)[0]
    assert "$(AI_ECHO)" in pg_block
    assert "$(if $(PYTEST_FLAGS)" in pg_block


def test_frontend_configs_enable_dot_reporter_and_silence_console_in_ai_mode() -> None:
    """Verify Vitest and Playwright configs emit dot output under IQOQO_AI_MODE."""
    vitest_cfg = (REPO_ROOT / "frontend" / "vitest.config.ts").read_text(encoding="utf-8")
    playwright_cfg = (REPO_ROOT / "frontend" / "playwright.config.ts").read_text(encoding="utf-8")

    assert 'reporter: "dot"' in vitest_cfg
    assert "onConsoleLog: () => false" in vitest_cfg
    assert 'process.env.IQOQO_AI_MODE === "1"' in playwright_cfg
    assert '["dot"]' in playwright_cfg


def test_live_pytest_ai_mode_emits_only_dots_and_summary() -> None:
    """Run a real pytest subprocess under IQOQO_AI_MODE=1 and assert strictly dots-only stdout."""
    env = dict(os.environ)
    env["IQOQO_AI_MODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_version.py"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 2, f"Expected strictly 2 terse lines (dots + summary), got: {lines!r}"
    assert re.fullmatch(r"\.+\s+\[\s*100%\]", lines[0]), f"Expected dot progress line, got: {lines[0]!r}"
    assert re.fullmatch(r"\d+ passed in [\d.]+s", lines[1]), f"Expected concise pass line, got: {lines[1]!r}"
