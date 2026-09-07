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
"""Full knowledge graph index builder for graphify."""

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
import run_update
import scan_context


def run_full_index(project_root: Path) -> int:
    """Run full graphify indexing workflow across code and context."""
    graphify_bin = run_update.find_graphify_bin()
    print(f"[iqoqo-graphify] Starting full index with {graphify_bin}...")

    # Step 1: Code AST extraction
    has_api_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    extract_cmd = [graphify_bin, "extract", "."]
    if not has_api_key:
        extract_cmd.append("--code-only")
    else:
        extract_cmd.extend(["--mode", "deep"])

    print(f"[iqoqo-graphify] Extracting code AST ({'deep' if has_api_key else 'code-only'})...")
    proc = subprocess.run(extract_cmd, check=False)
    if proc.returncode != 0:
        print(f"[iqoqo-graphify] Warning: graphify extract exited with code {proc.returncode}", file=sys.stderr)

    # Step 2: Scan context markdown files
    print("[iqoqo-graphify] Scanning .context/ markdown notes and ai-memory...")
    scan_context.main()

    # Step 3: Extract semantic entities
    print("[iqoqo-graphify] Extracting semantic entities from markdown chunks...")
    extract_semantic.main()

    # Step 4: Merge semantic chunks
    print("[iqoqo-graphify] Merging semantic extraction chunks...")
    merge_semantic.main()

    # Step 5: Merge AST + semantic
    print("[iqoqo-graphify] Merging code AST and semantic extraction graphs...")
    run_update.merge_ast_and_semantic(project_root)

    # Step 6: Cluster and report
    print("[iqoqo-graphify] Building communities and updating report...")
    subprocess.run([graphify_bin, "cluster-only", ".", "--no-label"], check=False)

    # Step 7: Status
    stats = get_status.get_graph_stats(project_root)
    get_status.print_status(stats)
    return 0


def main() -> None:
    """CLI entry point for run_index.py."""
    project_root = Path.cwd()
    sys.exit(run_full_index(project_root))


if __name__ == "__main__":
    main()
