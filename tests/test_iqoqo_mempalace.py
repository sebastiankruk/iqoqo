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
"""Unit tests for iqoqo-mempalace scoping and mining utilities."""

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
def mempalace_scan_module():
    """Load scan_scope module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-mempalace" / "scripts" / "scan_scope.py"
    return _load_module("iqoqo_mempalace_scan_scope", script_path)


@pytest.fixture
def mempalace_mine_module():
    """Load run_mine module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-mempalace" / "scripts" / "run_mine.py"
    return _load_module("iqoqo_mempalace_run_mine", script_path)


def test_should_exclude_ignores_sessions_and_covers(mempalace_scan_module):
    """Test should_exclude filters session caches and static image covers."""
    assert mempalace_scan_module.should_exclude("/path/to/.mykg_sessions/file.json")
    assert mempalace_scan_module.should_exclude("app/static/covers/cover_123.jpg")
    assert mempalace_scan_module.should_exclude("frontend/node_modules/react/index.js")
    assert mempalace_scan_module.should_exclude(".venv/lib/python3.14/site-packages/flask")

    assert not mempalace_scan_module.should_exclude("app/api/scanner.py")
    assert not mempalace_scan_module.should_exclude(".context/notes/sre/notes.md")


def test_resolve_scopes_identifies_codebase_and_notes(mempalace_scan_module):
    """Test resolve_scopes discovers codebase, notes, and convos scopes."""
    project_root = Path(__file__).parent.parent
    project_scopes, convos_scopes, _ = mempalace_scan_module.resolve_scopes(project_root)

    assert len(project_scopes) > 0
    assert len(convos_scopes) > 0

    project_paths = [s["path"] for s in project_scopes]
    assert "app" in project_paths
    assert "frontend" in project_paths
    assert "openspec/specs" in project_paths

    # Verify no .mykg_sessions or static/covers in project scope file lists
    for scope in project_scopes:
        for f in scope.get("files", []):
            assert ".mykg_sessions" not in f
            assert "app/static/covers" not in f

    # Verify conversation scopes
    convos_paths = [s["path"] for s in convos_scopes]
    assert any("ai-memory" in p for p in convos_paths)
    for s in convos_scopes:
        assert s["mode"] == "convos"


def test_mine_scope_executes_mempalace_command(mempalace_mine_module):
    """Test mine_scope formats correct CLI arguments."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        code = mempalace_mine_module.mine_scope("/usr/bin/mempalace", "app", mode="projects", wing="iqoqo", dry_run=True)

        assert code == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == [
            "/usr/bin/mempalace",
            "mine",
            "app",
            "--mode",
            "projects",
            "--wing",
            "iqoqo",
            "--dry-run",
        ]
