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
"""Unit tests for iqoqo-mykg autonomous daemon and update utilities."""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _load_module(name: str, file_path: Path) -> Any:
    """Dynamically load module from file path."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def agy_daemon_module():
    """Load agy_daemon module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-mykg" / "scripts" / "agy_daemon.py"
    return _load_module("iqoqo_mykg_agy_daemon", script_path)


@pytest.fixture
def run_update_module():
    """Load run_update module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-mykg" / "scripts" / "run_update.py"
    return _load_module("iqoqo_mykg_run_update", script_path)


def test_clean_json_fences(agy_daemon_module):
    """Test clean_json_fences strips markdown fences correctly."""
    clean = agy_daemon_module.clean_json_fences
    assert clean('```json\n{"nodes": []}\n```') == '{"nodes": []}'
    assert clean('```\n{"nodes": []}\n```') == '{"nodes": []}'
    assert clean('  {"nodes": []}  ') == '{"nodes": []}'


def test_process_task_success(agy_daemon_module, tmp_path):
    """Test process_task executes agy and writes answer and done files atomically."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()

    task_id = "abc123taskid"
    task_file = inbox / f"{task_id}.task.json"
    task_file.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "system": "Extract nodes",
                "user": "Input document text",
            }
        ),
        encoding="utf-8",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='```json\n{"nodes": ["N1"]}\n```', stderr="")

        success = agy_daemon_module.process_task(task_file, outbox)
        assert success is True

        # Verify agy was called with expected arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "agy"
        assert "--dangerously-skip-permissions" in args
        assert "-p" in args
        assert "--model" in args
        assert args[args.index("--model") + 1] == "gemini-3.7-flash-low"
        assert "--effort" in args
        assert args[args.index("--effort") + 1] == "low"

        # Verify output files
        done_file = outbox / f"{task_id}.done"
        answer_file = outbox / f"{task_id}.answer.json"
        assert done_file.exists()
        assert answer_file.exists()

        answer_data = json.loads(answer_file.read_text(encoding="utf-8"))
        assert answer_data["task_id"] == task_id
        assert answer_data["answer"] == '{"nodes": ["N1"]}'


def test_process_task_with_model_and_effort(agy_daemon_module, tmp_path):
    """Test process_task forwards model and effort flags to agy CLI."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()

    task_id = "test_model_effort"
    task_file = inbox / f"{task_id}.task.json"
    task_file.write_text(json.dumps({"task_id": task_id, "user": "extract"}), encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='{"nodes": []}', stderr="")
        success = agy_daemon_module.process_task(
            task_file,
            outbox,
            model="gemini-3.7-flash-high",
            effort="high",
        )
        assert success is True
        args = mock_run.call_args[0][0]
        assert "--model" in args
        assert args[args.index("--model") + 1] == "gemini-3.7-flash-high"
        assert "--effort" in args
        assert args[args.index("--effort") + 1] == "high"


def test_process_task_with_env_vars(agy_daemon_module, tmp_path, monkeypatch):
    """Test process_task falls back to MYKG_MODEL and MYKG_EFFORT environment variables."""
    monkeypatch.setenv("MYKG_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("MYKG_EFFORT", "medium")

    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()

    task_id = "test_env_vars"
    task_file = inbox / f"{task_id}.task.json"
    task_file.write_text(json.dumps({"task_id": task_id, "user": "extract"}), encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='{"nodes": []}', stderr="")
        success = agy_daemon_module.process_task(task_file, outbox)
        assert success is True
        args = mock_run.call_args[0][0]
        assert "--model" in args
        assert args[args.index("--model") + 1] == "claude-sonnet-4-6"
        assert "--effort" in args
        assert args[args.index("--effort") + 1] == "medium"


def test_process_task_already_done(agy_daemon_module, tmp_path):
    """Test process_task skips already finished tasks."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()

    task_id = "done123"
    task_file = inbox / f"{task_id}.task.json"
    task_file.write_text(json.dumps({"task_id": task_id}), encoding="utf-8")

    (outbox / f"{task_id}.done").touch()
    (outbox / f"{task_id}.answer.json").write_text('{"task_id": "done123"}', encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        success = agy_daemon_module.process_task(task_file, outbox)
        assert success is True
        mock_run.assert_not_called()


def test_prepare_scope_path_directory(run_update_module, tmp_path):
    """Test prepare_scope_path returns directory directly without creating temp dir."""
    test_dir = tmp_path / "app"
    test_dir.mkdir()

    path_str, is_temp = run_update_module.prepare_scope_path([str(test_dir)])
    assert path_str == str(test_dir)
    assert is_temp is False


def test_prepare_scope_path_files_creates_temp_dir(run_update_module, tmp_path):
    """Test prepare_scope_path wraps loose files into a temporary directory."""
    file1 = tmp_path / "Makefile"
    file2 = tmp_path / "Dockerfile"
    file1.write_text("all:\n\t@true", encoding="utf-8")
    file2.write_text("FROM scratch", encoding="utf-8")

    path_str, is_temp = run_update_module.prepare_scope_path([str(file1), str(file2)])
    assert is_temp is True
    temp_dir = Path(path_str)
    assert temp_dir.is_dir()
    assert (temp_dir / "Makefile").exists()
    assert (temp_dir / "Dockerfile").exists()
    assert (temp_dir / "Makefile").read_text(encoding="utf-8") == "all:\n\t@true"

    import shutil

    shutil.rmtree(temp_dir)


def test_get_latest_session_finds_newest(run_update_module, tmp_path):
    """Test get_latest_session discovers newest timestamp directory."""
    sessions_dir = tmp_path / "mykg_sessions"
    sessions_dir.mkdir()

    s1 = sessions_dir / "2026-08-20T10-00-00"
    s2 = sessions_dir / "2026-08-25T12-00-00"
    s1.mkdir()
    s2.mkdir()

    latest = run_update_module.get_latest_session(tmp_path)
    assert latest in ["2026-08-20T10-00-00", "2026-08-25T12-00-00"]
