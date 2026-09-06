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
"""Show mykg session status and indexed scope statistics.

Reads session data from mykg_sessions/ and .iqoqo-mykg/ state.
"""

import json
from pathlib import Path


def get_latest_session(project_root: Path) -> tuple:
    """Find the most recent mykg session. Returns (name, path) or (None, None)."""
    sessions_dir = project_root / "mykg_sessions"
    if not sessions_dir.exists() or not sessions_dir.is_symlink():
        sessions_dir = project_root / ".mykg_sessions"

    if not sessions_dir.exists():
        return None, None

    sessions = []
    for item in sessions_dir.iterdir():
        if item.is_dir():
            try:
                sessions.append((item.name, item, item.stat().st_mtime))
            except OSError:
                continue

    if not sessions:
        return None, None

    sessions.sort(key=lambda x: x[2], reverse=True)
    return sessions[0][0], sessions[0][1]


def count_nodes_edges(session_path: Path) -> tuple:
    """Count nodes and edges from session output."""
    kg_json = session_path / "output" / "networkx_output" / "knowledge_graph.json"
    edges_txt = session_path / "output" / "networkx_output" / "edges_nx.txt"

    node_count = 0
    edge_count = 0

    if kg_json.exists():
        try:
            data = json.loads(kg_json.read_text())
            node_count = len(data.get("nodes", []))
        except (OSError, json.JSONDecodeError):
            pass

    if edges_txt.exists():
        try:
            with open(edges_txt) as f:
                edge_count = sum(1 for _ in f)
        except OSError:
            pass

    if node_count == 0 or edge_count == 0:
        nodes_file = session_path / "output" / "nodes.jsonl"
        edges_file = session_path / "output" / "edges.jsonl"
        if not nodes_file.exists():
            nodes_file = session_path / "intermediate" / "nodes.jsonl"
        if not edges_file.exists():
            edges_file = session_path / "intermediate" / "edges.jsonl"

        if node_count == 0 and nodes_file.exists():
            with open(nodes_file) as f:
                node_count = sum(1 for _ in f)

        if edge_count == 0 and edges_file.exists():
            with open(edges_file) as f:
                edge_count = sum(1 for _ in f)

    return node_count, edge_count


def get_session_outputs(session_path: Path) -> dict:
    """Get output artifact locations."""
    outputs = {}
    output_dir = session_path / "output"

    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.is_dir():
                outputs[item.name] = str(item)
            elif item.suffix in [".ttl", ".md", ".json"]:
                outputs[item.name] = str(item)

    return outputs


def main():
    project_root = Path.cwd()
    state_dir = project_root / ".iqoqo-mykg"

    print("=" * 60)
    print("iqoqo-mykg Session Status")
    print("=" * 60)

    # Latest session
    session_name, session_path = get_latest_session(project_root)

    if not session_name:
        print("\nNo mykg sessions found.")
        print("Run 'iqoqo-mykg index' to create your first session.")
        return

    print(f"\nLatest Session: {session_name}")
    print(f"Path: {session_path}")

    # Node/edge counts
    node_count, edge_count = count_nodes_edges(session_path)
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {node_count}")
    print(f"  Edges: {edge_count}")

    # Output artifacts
    outputs = get_session_outputs(session_path)
    if outputs:
        print(f"\nOutput Artifacts:")
        for name, path in sorted(outputs.items()):
            print(f"  {name}: {path}")

    # Indexed scopes
    manifest_file = state_dir / "scope_manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text())
        scopes = manifest.get("scopes", {})

        print(f"\nIndexed Scopes ({len(scopes)}):")
        for scope_name, paths in scopes.items():
            if paths:
                path_str = paths[0]
                if len(paths) > 1:
                    path_str += f" (+{len(paths)-1} more)"
                print(f"  {scope_name}: {path_str}")
            else:
                print(f"  {scope_name}: (empty)")

        version = manifest.get("version", "unknown")
        print(f"\nVersion: {version}")
    else:
        print("\nNo scope manifest found. Run scan_scope.py to see indexed scopes.")

    # Session history
    sessions_dir = project_root / "mykg_sessions"
    if not sessions_dir.exists() or not sessions_dir.is_symlink():
        sessions_dir = project_root / ".mykg_sessions"

    if sessions_dir.exists():
        all_sessions = []
        for item in sessions_dir.iterdir():
            if item.is_dir():
                try:
                    all_sessions.append((item.name, item.stat().st_mtime))
                except OSError:
                    continue

        if len(all_sessions) > 1:
            print(f"\nSession History ({len(all_sessions)} total):")
            all_sessions.sort(key=lambda x: x[1], reverse=True)
            for name, mtime in all_sessions[:5]:
                print(f"  {name}")
            if len(all_sessions) > 5:
                print(f"  ... and {len(all_sessions) - 5} more")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
