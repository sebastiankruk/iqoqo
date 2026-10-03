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
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Tests for the container image size gate.

The gate exists because the previous target was a "<500 MB" line in a prose
requirement that went unmet for a whole release (1019.2 MB -> 826.7 MB) with
nothing failing. A gate that can be quietly disabled is not a gate, so these
tests assert both directions: over budget fails loudly, and no amount of
editing the budget file or the wiring turns a failure into a pass.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Load the gate by file path rather than putting scripts/ on sys.path.
# scripts/ contains its own `migrations/` package, so inserting it at the front of
# sys.path shadows the repository's top-level `migrations` for the whole session
# and every later Alembic test fails with "No module named 'migrations.versions'".
# An import by path has no global side effect.
_spec = importlib.util.spec_from_file_location("check_image_size", ROOT / "scripts" / "check_image_size.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

MB = gate.MB
BUDGET_FILE = ROOT / "deploy" / "image-size-budget.txt"
BUILD_SCRIPT = ROOT / "scripts" / "build_docker_images.sh"


class FakeCompleted:
    """Minimal stand-in for subprocess.Completed."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# ── Budget file parsing ─────────────────────────────────────────────────────


def test_shipped_budget_file_parses_and_is_positive():
    """The file the build actually reads must be valid and finite."""
    budget = gate.read_budget(BUDGET_FILE)
    assert set(budget) == set(gate.REQUIRED_KEYS)
    assert 0 < budget["MAX_BYTES"] < 2 * 1024 * MB, f"implausible budget {budget['MAX_BYTES']} bytes"
    assert 0 < budget["MEASURED_BYTES"] <= budget["MAX_BYTES"]


def test_budget_records_a_measurement_and_leaves_tight_headroom():
    """A limit with no recorded measurement is the old failure mode again."""
    budget = gate.read_budget(BUDGET_FILE)
    headroom = budget["MAX_BYTES"] - budget["MEASURED_BYTES"]
    assert headroom > 0, "the current image must actually be under budget"
    # Small on purpose: this is a regression detector, not a growth allowance.
    assert headroom < budget["MEASURED_BYTES"] * 0.1, f"headroom {headroom} is too loose to catch a regression"


def test_parse_budget_ignores_comments_and_whitespace():
    parsed = gate.parse_budget("# a comment\n\n  MAX_BYTES = 1234  \nMEASURED_BYTES=1000\n")
    assert parsed == {"MAX_BYTES": 1234, "MEASURED_BYTES": 1000}


@pytest.mark.parametrize(
    "contents",
    [
        "",  # blank file: must not mean "unlimited"
        "# MAX_BYTES=1\n",  # commented out
        "MAX_BYTES=0\nMEASURED_BYTES=1\n",  # zero would let any image through
        "MAX_BYTES=-5\nMEASURED_BYTES=1\n",
        "MAX_BYTES=notanumber\nMEASURED_BYTES=1\n",
        "MAX_BYTES=\nMEASURED_BYTES=1\n",
        "SOMETHING_ELSE=10\n",
        "MAX_BYTES=1000\n",  # a budget without a measurement is unexplained
        "MEASURED_BYTES=1000\n",
    ],
)
def test_unusable_budget_is_rejected_loudly(contents):
    """Defaulting to unlimited is the same as disabling the gate."""
    with pytest.raises(ValueError):
        gate.parse_budget(contents)


def test_measurement_above_the_budget_is_rejected():
    """A budget its own recorded measurement already exceeds is incoherent."""
    with pytest.raises(ValueError, match="exceeds MAX_BYTES"):
        gate.parse_budget("MAX_BYTES=1000\nMEASURED_BYTES=2000\n")


# ── The comparison itself ───────────────────────────────────────────────────


def test_over_budget_fails():
    within, message = gate.evaluate(700 * MB, 671 * MB)
    assert within is False
    assert "EXCEEDS" in message
    assert "29.0 MB" in message, message


def test_under_budget_passes():
    within, message = gate.evaluate(670 * MB, 671 * MB)
    assert within is True
    assert "within budget" in message


def test_exactly_at_the_limit_passes():
    """<= is within budget; the ceiling is a ceiling, not a threshold to cross."""
    assert gate.evaluate(671 * MB, 671 * MB)[0] is True


def test_one_byte_over_the_limit_fails():
    assert gate.evaluate(671 * MB + 1, 671 * MB)[0] is False


def test_failure_reports_how_much_and_by_how_much():
    """An operator needs the delta, not just a red cross."""
    _, message = gate.evaluate(700 * MB, 671 * MB)
    assert "700.0 MB" in message
    assert "671.0 MB" in message
    assert "29.0 MB" in message


# ── The CLI, with docker stubbed out ───────────────────────────────────────


def test_cli_returns_nonzero_over_budget(monkeypatch, capsys):
    monkeypatch.setattr(gate, "image_size", lambda image: 700 * MB)
    monkeypatch.setattr(gate, "read_budget", lambda path=None: {"MAX_BYTES": 671 * MB, "MEASURED_BYTES": 660 * MB})
    monkeypatch.setattr(gate, "breakdown", lambda image, limit=15: "  breakdown")
    monkeypatch.setattr(sys, "argv", ["check_image_size.py", "iqoqo-backend:test"])

    assert gate.main() == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.err
    assert "breakdown" in captured.err


def test_cli_returns_zero_under_budget(monkeypatch, capsys):
    monkeypatch.setattr(gate, "image_size", lambda image: 660 * MB)
    monkeypatch.setattr(gate, "read_budget", lambda path=None: {"MAX_BYTES": 671 * MB, "MEASURED_BYTES": 660 * MB})
    monkeypatch.setattr(sys, "argv", ["check_image_size.py", "iqoqo-backend:test", "--quiet"])

    assert gate.main() == 0
    assert "within budget" not in capsys.readouterr().out


def test_cli_fails_when_the_budget_file_is_unreadable(monkeypatch, tmp_path):
    """A missing or blank budget must fail the build, not pass it."""
    broken = tmp_path / "budget.txt"
    broken.write_text("# nothing here\n", encoding="utf-8")
    monkeypatch.setattr(gate, "image_size", lambda image: 1 * MB)
    monkeypatch.setattr(sys, "argv", ["check_image_size.py", "iqoqo-backend:test", "--budget-file", str(broken)])

    with pytest.raises(SystemExit) as exc:
        gate.main()
    assert exc.value.code != 0


def test_image_size_uses_docker_image_inspect(monkeypatch):
    """The compared number must be measured, not estimated from layer metadata."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted(stdout="123456\n")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    assert gate.image_size("iqoqo-backend:test") == 123456
    assert captured["cmd"][:3] == ["docker", "image", "inspect"]
    assert "iqoqo-backend:test" in captured["cmd"]


def test_image_size_exits_when_docker_fails(monkeypatch):
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: FakeCompleted(stderr="no such image", returncode=1))
    with pytest.raises(SystemExit) as exc:
        gate.image_size("iqoqo-backend:nope")
    assert "cannot inspect image" in str(exc.value)


# ── Failure output: the breakdown ───────────────────────────────────────────


def test_breakdown_names_the_watched_paths(monkeypatch):
    """A failure has to identify the cause without another multi-minute build."""
    monkeypatch.setattr(gate, "_du", lambda image, path: 123)
    monkeypatch.setattr(
        gate,
        "_du_children",
        lambda image, parent: [(100, f"{parent}/scipy"), (50, f"{parent}/numpy")],
    )

    report = gate.breakdown("iqoqo-backend:test")
    for path in gate.WATCHED_PATHS:
        assert path in report, path
    assert "scipy" in report, "the fat dependency must be named, not just the directory total"
    assert "numpy" in report
    assert "image-size-budget.txt" in report


def test_du_children_expands_the_glob_through_a_shell(monkeypatch):
    """`du` does not glob, and `docker run` has no shell unless asked."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted(stdout="30\t/usr/local/lib/python3.14/site-packages/scipy\n")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    assert gate._du_children("img", "/sp") == [(30, "/usr/local/lib/python3.14/site-packages/scipy")]
    assert "sh" in captured["cmd"], "the glob needs a shell in the container"
    assert "du -sm -- /sp/*" in captured["cmd"]


def test_du_children_survives_a_failing_container(monkeypatch):
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: FakeCompleted(stderr="du: no", returncode=1))
    assert gate._du_children("img", "/sp") == []


def test_breakdown_survives_a_missing_du(monkeypatch):
    """A stripped runtime stage must not turn the diagnostic into a crash."""
    monkeypatch.setattr(gate.shutil, "which", lambda name: None)
    assert "du not available" in gate.breakdown("iqoqo-backend:test")


def test_breakdown_skips_paths_du_cannot_measure(monkeypatch):
    monkeypatch.setattr(gate, "_du", lambda image, path: None)
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: FakeCompleted(stdout=""))
    report = gate.breakdown("iqoqo-backend:test")
    assert "iqoqo-backend:test" in report


# ── Wiring: the build must actually call it ─────────────────────────────────


def test_build_script_runs_the_gate_and_fails_on_error():
    """A gate nobody invokes is decoration."""
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "check_image_size.py" in script, "build_docker_images.sh must invoke the gate"

    # The invocation must be followed by an `|| { ... exit 1 }` guard. Match the
    # closing brace by scanning forward line by line: the invocation itself
    # contains a `}` inside "${TAG}", so a plain index() would stop there.
    lines = script.splitlines()
    call_index = next(i for i, line in enumerate(lines) if "check_image_size.py" in line and "python" not in line)
    assert "|| {" in lines[call_index], f"gate call is not guarded: {lines[call_index]!r}"

    guard = []
    for line in lines[call_index + 1 :]:
        guard.append(line)
        if line.strip() == "}":
            break
    else:
        raise AssertionError("gate call's guard is never closed")
    assert "exit 1" in "\n".join(guard), f"the guard does not abort the build: {guard}"


def test_gate_runs_before_the_success_message_is_printed():
    """Ordering matters: 'built successfully' must not precede the gate."""
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert script.index("check_image_size.py") < script.index("Backend image built successfully!")


# ── End to end, with docker stubbed ─────────────────────────────────────────


def test_gate_fails_a_real_invocation_over_budget(tmp_path):
    """Full CLI against a fake docker: the exit code a build would see."""
    budget = tmp_path / "budget.txt"
    budget.write_text("MAX_BYTES=104857600\nMEASURED_BYTES=104857600\n", encoding="utf-8")  # 100 MB

    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = "image" ]; then echo 209715200; exit 0; fi\n'  # 200 MB
        'if [ "$1" = "run" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    env = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "HOME": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_image_size.py"),
            "iqoqo-backend:test",
            "--budget-file",
            str(budget),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 1, result.stderr
    assert "FAILED" in result.stderr
