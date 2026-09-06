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
"""Autonomous incremental update runner for graphify knowledge graph."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add scripts folder to sys.path for internal imports
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import extract_semantic
import get_status
import merge_semantic
import scan_context


def find_graphify_bin() -> str:
    """Find the graphify CLI executable."""
    venv_bin = Path.cwd() / ".venv" / "bin" / "graphify"
    if venv_bin.exists():
        return str(venv_bin)
    which_bin = shutil.which("graphify")
    if which_bin:
        return which_bin
    return "graphify"


def merge_ast_and_semantic(project_root: Path) -> bool:
    """Merge AST and semantic graph files into .graphify_extract.json."""
    ast_file = project_root / "graphify-out" / ".graphify_ast.json"
    sem_file = project_root / "graphify-out" / ".graphify_semantic.json"
    out_file = project_root / "graphify-out" / ".graphify_extract.json"

    if not sem_file.exists():
        return False

    ast_data = {"nodes": [], "edges": []}
    if ast_file.exists():
        try:
            ast_data = json.loads(ast_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        sem_data = json.loads(sem_file.read_text(encoding="utf-8"))
    except Exception:
        sem_data = {"nodes": [], "edges": []}

    seen = {n["id"] for n in ast_data.get("nodes", [])}
    merged_nodes = list(ast_data.get("nodes", []))
    for n in sem_data.get("nodes", []):
        if n.get("id") and n["id"] not in seen:
            merged_nodes.append(n)
            seen.add(n["id"])

    merged = {
        "nodes": merged_nodes,
        "edges": ast_data.get("edges", []) + sem_data.get("edges", []),
        "hyperedges": sem_data.get("hyperedges", []),
        "input_tokens": sem_data.get("input_tokens", 0),
        "output_tokens": sem_data.get("output_tokens", 0),
    }

    out_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return True


def run_incremental_update(project_root: Path) -> int:
    """Run full incremental update workflow."""
    graphify_bin = find_graphify_bin()
    print(f"[iqoqo-graphify] Updating code graph using {graphify_bin}...")

    # Step 1: Update AST code graph
    proc = subprocess.run([graphify_bin, "update", "."], check=False)
    if proc.returncode != 0:
        print(f"[iqoqo-graphify] Warning: graphify update exited with code {proc.returncode}", file=sys.stderr)

    # Step 2: Check .context/ changes
    print("[iqoqo-graphify] Checking .context/ changes...")
    context_changed = False
    try:
        # Check if manifest needs update
        manifest_file = project_root / "graphify-out" / "manifest.json"
        if not manifest_file.exists():
            context_changed = True
        else:
            # Run scan_context to see if chunks changed
            scan_context.main()
            context_changed = True
    except Exception as exc:
        print(f"[iqoqo-graphify] Note during context scan: {exc}")
        context_changed = True

    # Step 3 & 4: Extract and merge semantic entities if needed
    if context_changed:
        print("[iqoqo-graphify] Extracting semantic markdown entities...")
        extract_semantic.main()
        print("[iqoqo-graphify] Merging semantic extraction chunks...")
        merge_semantic.main()

    # Step 5: Merge AST + semantic
    merge_ast_and_semantic(project_root)

    # Step 6: Cluster and report
    print("[iqoqo-graphify] Building communities and updating report...")
    cluster_proc = subprocess.run([graphify_bin, "cluster-only", ".", "--no-label"], check=False)
    if cluster_proc.returncode != 0:
        # Fallback without cluster-only if not supported
        pass

    # Step 7: Print status
    stats = get_status.get_graph_stats(project_root)
    get_status.print_status(stats)
    return 0


def main() -> None:
    """CLI entry point for run_update.py."""
    project_root = Path.cwd()
    sys.exit(run_incremental_update(project_root))


if __name__ == "__main__":
    main()
