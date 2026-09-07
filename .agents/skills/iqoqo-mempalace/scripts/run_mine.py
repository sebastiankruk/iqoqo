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
"""Execute scoped MemPalace mining for iqoqo.

Mines codebase and selected notes as projects (--mode projects --wing iqoqo)
and versioned AI session memory as conversations (--mode convos --wing iqoqo).
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional


def find_mempalace() -> str:
    """Find mempalace executable."""
    venv_bin = Path.cwd() / ".venv" / "bin" / "mempalace"
    if venv_bin.exists():
        return str(venv_bin)

    system_bin = shutil.which("mempalace")
    if system_bin:
        return system_bin

    print("Error: mempalace CLI not found in .venv or system PATH.", file=sys.stderr)
    sys.exit(1)


def run_cmd(cmd: List[str]) -> int:
    """Run a shell command."""
    print(f"\n>> {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    return result.returncode


def mine_scope(mempalace_bin: str, target: str, mode: str, wing: str = "iqoqo", dry_run: bool = False) -> int:
    """Execute mempalace mine for a given scope."""
    cmd = [mempalace_bin, "mine", target, "--mode", mode, "--wing", wing]
    if dry_run:
        cmd.append("--dry-run")
    return run_cmd(cmd)


def main() -> None:
    """Main CLI entry point for run_mine."""
    parser = argparse.ArgumentParser(description="Mine scoped iQoQo assets into MemPalace")
    parser.add_argument("target", nargs="?", help="Optional specific file or directory to mine")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying palace")
    parser.add_argument("--mode", choices=["projects", "convos"], help="Explicit ingest mode for specific target")
    parser.add_argument("--wing", default="iqoqo", help="Palace wing (default: iqoqo)")
    args = parser.parse_args()

    project_root = Path.cwd()
    mempalace_bin = find_mempalace()

    # If single target provided:
    if args.target:
        target_path = Path(args.target)
        if not target_path.exists():
            print(f"Error: Target path does not exist: {args.target}", file=sys.stderr)
            sys.exit(1)

        # Detect mode if not specified
        mode = args.mode
        if not mode:
            if "ai-memory" in str(target_path):
                mode = "convos"
            else:
                mode = "projects"

        code = mine_scope(mempalace_bin, str(target_path), mode=mode, wing=args.wing, dry_run=args.dry_run)
        sys.exit(code)

    # Full batch run across manifest
    state_dir = project_root / ".iqoqo-mempalace"
    manifest_file = state_dir / "scope_manifest.json"

    if not manifest_file.exists():
        print("Manifest missing. Generating scope manifest...")
        scan_script = project_root / ".agents" / "skills" / "iqoqo-mempalace" / "scripts" / "scan_scope.py"
        subprocess.run([sys.executable, str(scan_script)], check=True)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    project_scopes = manifest.get("project_scopes", [])
    convos_scopes = manifest.get("convos_scopes", [])
    wing = manifest.get("wing", "iqoqo")

    start_time = time.time()
    total_processed = 0

    print("=" * 60)
    print(f"  Starting iQoQo Scoped MemPalace Mining (Wing: {wing})")
    print("=" * 60)

    # Mine project scopes
    for scope in project_scopes:
        path = scope["path"]
        print(f"\n--- Mining Project Scope: {path} ---")
        code = mine_scope(mempalace_bin, path, mode="projects", wing=wing, dry_run=args.dry_run)
        if code == 0:
            total_processed += scope.get("count", 1)

    # Mine conversation scopes
    for scope in convos_scopes:
        path = scope["path"]
        print(f"\n--- Mining Conversation Scope (AI Memory): {path} ---")
        code = mine_scope(mempalace_bin, path, mode="convos", wing=wing, dry_run=args.dry_run)
        if code == 0:
            total_processed += scope.get("count", 1)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  MemPalace Mining Complete! (Time: {elapsed:.2f}s, Processed: ~{total_processed} items)")
    print("=" * 60)


if __name__ == "__main__":
    main()
