#!/usr/bin/env python3
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
"""Display status and statistics of the graphify knowledge graph."""

import json
from pathlib import Path
from typing import Any, Dict


def get_graph_stats(project_root: Path) -> Dict[str, Any]:
    """Load and return graph statistics from graphify-out/."""
    graph_path = project_root / "graphify-out" / "graph.json"
    report_path = project_root / "graphify-out" / "GRAPH_REPORT.md"
    html_path = project_root / "graphify-out" / "visualizations" / "graph.html"
    sem_path = project_root / "graphify-out" / ".graphify_semantic.json"

    if not graph_path.exists():
        return {
            "exists": False,
            "error": "No graphify-out/graph.json found. Run make graphify-index first.",
        }

    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {
            "exists": False,
            "error": f"Failed to parse graph.json: {exc}",
        }

    nodes = data.get("nodes", [])
    edges = data.get("links", data.get("edges", []))

    # Count unique communities
    communities = {n.get("community") for n in nodes if n.get("community") is not None}

    sem_nodes_count = 0
    if sem_path.exists():
        try:
            sem_data = json.loads(sem_path.read_text(encoding="utf-8"))
            sem_nodes_count = len(sem_data.get("nodes", []))
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    return {
        "exists": True,
        "graph_path": str(graph_path),
        "report_path": str(report_path) if report_path.exists() else None,
        "html_path": str(html_path) if html_path.exists() else None,
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "communities_count": len(communities),
        "semantic_nodes_count": sem_nodes_count,
    }


def print_status(stats: Dict[str, Any]) -> None:
    """Format and print graph status."""
    print("=" * 60)
    print("iqoqo-graphify Knowledge Graph Status")
    print("=" * 60)

    if not stats.get("exists"):
        print(f"Status: NOT FOUND ({stats.get('error')})")
        print("=" * 60)
        return

    print(f"\nGraph Path: {stats.get('graph_path')}")
    print("\nGraph Statistics:")
    print(f"  Nodes: {stats.get('nodes_count'):,}")
    print(f"  Edges: {stats.get('edges_count'):,}")
    print(f"  Communities: {stats.get('communities_count'):,}")
    if stats.get("semantic_nodes_count"):
        print(f"  Semantic (.context) Nodes: {stats.get('semantic_nodes_count'):,}")

    print("\nOutput Artifacts:")
    if stats.get("report_path"):
        print(f"  Report: {stats.get('report_path')}")
    if stats.get("html_path"):
        print(f"  Visualization: {stats.get('html_path')}")

    print("=" * 60)


def main() -> None:
    """CLI entry point for get_status.py."""
    project_root = Path.cwd()
    stats = get_graph_stats(project_root)
    print_status(stats)


if __name__ == "__main__":
    main()
