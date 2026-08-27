#!/usr/bin/env python3
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
    nodes_file = session_path / "intermediate" / "nodes.jsonl"
    edges_file = session_path / "intermediate" / "edges.jsonl"

    node_count = 0
    edge_count = 0

    if nodes_file.exists():
        with open(nodes_file) as f:
            node_count = sum(1 for _ in f)

    if edges_file.exists():
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
            elif item.suffix in ['.ttl', '.md', '.json']:
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
