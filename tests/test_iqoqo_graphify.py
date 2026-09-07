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
"""Unit tests for iqoqo-graphify autonomous runner and utility scripts."""

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
def run_update_module():
    """Load run_update module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-graphify" / "scripts" / "run_update.py"
    return _load_module("iqoqo_graphify_run_update", script_path)


@pytest.fixture
def get_status_module():
    """Load get_status module."""
    script_path = Path(__file__).parent.parent / ".agents" / "skills" / "iqoqo-graphify" / "scripts" / "get_status.py"
    return _load_module("iqoqo_graphify_get_status", script_path)


def test_find_graphify_bin(run_update_module):
    """Test find_graphify_bin discovers graphify executable."""
    bin_path = run_update_module.find_graphify_bin()
    assert "graphify" in bin_path


def test_merge_ast_and_semantic(run_update_module, tmp_path):
    """Test merge_ast_and_semantic combines AST and semantic files."""
    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    ast_file = graphify_out / ".graphify_ast.json"
    ast_file.write_text(json.dumps({"nodes": [{"id": "node1"}], "edges": [{"source": "node1", "target": "node2"}]}))

    sem_file = graphify_out / ".graphify_semantic.json"
    sem_file.write_text(json.dumps({"nodes": [{"id": "node2"}], "edges": [], "hyperedges": []}))

    merged = run_update_module.merge_ast_and_semantic(tmp_path)
    assert merged is True

    extract_file = graphify_out / ".graphify_extract.json"
    assert extract_file.exists()
    data = json.loads(extract_file.read_text())
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1


def test_get_graph_stats(get_status_module, tmp_path):
    """Test get_graph_stats parses graph.json."""
    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    graph_file = graphify_out / "graph.json"
    graph_file.write_text(
        json.dumps(
            {
                "nodes": [{"id": "n1", "community": 1}, {"id": "n2", "community": 2}],
                "edges": [{"source": "n1", "target": "n2"}],
            }
        )
    )

    stats = get_status_module.get_graph_stats(tmp_path)
    assert stats["exists"] is True
    assert stats["nodes_count"] == 2
    assert stats["edges_count"] == 1
    assert stats["communities_count"] == 2
