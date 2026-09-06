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
"""Run incremental mykg update for changed scopes only.

Reads changed scopes from .iqoqo-mykg/changed_scopes.json.
Appends to the latest session.

Supports --grow-schema to use --append-with-grow-schema.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


def get_mykg_path() -> str:
    """Find mykg executable."""
    venv_path = Path.cwd() / ".venv" / "bin" / "mykg"
    if venv_path.exists():
        return str(venv_path)

    result = subprocess.run(["which", "mykg"], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result.stdout.strip()

    print("Error: mykg not found. Install it or ensure .venv/bin/mykg exists.")
    sys.exit(1)


def get_latest_session(project_root: Path) -> Optional[str]:
    """Find the most recent mykg session."""
    sessions_dir = project_root / "mykg_sessions"
    if not sessions_dir.exists():
        sessions_dir = project_root / ".mykg_sessions"

    if not sessions_dir.exists():
        return None

    sessions = []
    for item in sessions_dir.iterdir():
        if item.is_dir():
            try:
                sessions.append((item.name, item.stat().st_mtime))
            except (ValueError, OSError):
                continue

    if not sessions:
        return None

    sessions.sort(key=lambda x: x[1], reverse=True)
    return sessions[0][0]


def prepare_scope_path(paths: List[str]) -> Tuple[str, bool]:
    """Ensure scope path is a directory. If paths are files, copy them to a temp dir.

    Returns (path_to_extract, is_temporary).
    """
    if not paths:
        return "", False

    first_path = Path(paths[0])
    if first_path.is_dir():
        return str(first_path), False

    temp_dir = tempfile.mkdtemp(prefix="iqoqo_mykg_scope_")
    for file_str in paths:
        src = Path(file_str)
        if src.is_file():
            dst = Path(temp_dir) / src.name
            shutil.copy2(src, dst)
        elif src.is_dir():
            dst = Path(temp_dir) / src.name
            shutil.copytree(src, dst)

    return temp_dir, True


def run_extract(mykg_path: str, scope_path: str, session: str, grow_schema: bool = False) -> bool:
    """Run mykg extract-graph for a scope. Returns success."""
    cmd = [mykg_path, "extract-graph", scope_path, "--append", "--session", session, "--profile", "agent-claude-code"]

    if grow_schema:
        cmd.append("--append-with-grow-schema")

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


def main():
    project_root = Path.cwd()
    state_dir = project_root / ".iqoqo-mykg"
    changed_file = state_dir / "changed_scopes.json"
    grow_schema = "--grow-schema" in sys.argv or "--grow" in sys.argv

    # Get latest session
    session = get_latest_session(project_root)
    if not session:
        print("Error: No existing mykg session found.")
        print("Run 'iqoqo-mykg index' first to create a session.")
        sys.exit(1)

    print(f"Using session: {session}")

    # Check if we have specific changed scopes
    if changed_file.exists():
        changed_scopes = json.loads(changed_file.read_text())
    else:
        # If no changed_scopes file, try to load from scope manifest
        manifest_file = state_dir / "scope_manifest.json"
        if manifest_file.exists():
            manifest = json.loads(manifest_file.read_text())
            changed_scopes = manifest.get("scopes", {})
            print("No change detection run. Will attempt to update all scopes.")
        else:
            print("Error: No scope manifest found. Run scan_scope.py first.")
            sys.exit(1)

    if not changed_scopes:
        print("No scopes have changed. Nothing to update.")
        sys.exit(0)

    mykg_path = get_mykg_path()
    mode = "GROW SCHEMA" if grow_schema else "APPEND"

    print(f"\nUpdating {len(changed_scopes)} changed scope(s) with {mode}...")

    success_count = 0
    for scope_name, paths in changed_scopes.items():
        if not paths:
            print(f"\nSkipping empty scope: {scope_name}")
            continue

        scope_path, is_temp = prepare_scope_path(paths)
        print(f"\n[{success_count+1}/{len(changed_scopes)}] Updating: {scope_name}")
        print(f"  Path: {scope_path} {'(temporary directory)' if is_temp else ''}")
        print(f"  Mode: {mode}")

        try:
            if run_extract(mykg_path, scope_path, session, grow_schema):
                success_count += 1
            else:
                print(f"  Warning: Failed to update {scope_name}")
        finally:
            if is_temp and Path(scope_path).exists():
                shutil.rmtree(scope_path, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"Update complete: {success_count}/{len(changed_scopes)} scopes updated")
    print(f"Session: {session}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
