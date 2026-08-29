#!/usr/bin/env python3
"""Run full mykg index across all configured scopes.

Reads scope manifest from .iqoqo-mykg/scope_manifest.json.
First scope creates a new session; subsequent scopes use --append.
"""

import json
import subprocess
import sys
from pathlib import Path


def get_mykg_path() -> str:
    """Find mykg executable."""
    # Check venv first
    venv_path = Path.cwd() / ".venv" / "bin" / "mykg"
    if venv_path.exists():
        return str(venv_path)

    # Check PATH
    result = subprocess.run(["which", "mykg"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    print("Error: mykg not found. Install it or ensure .venv/bin/mykg exists.")
    sys.exit(1)


def run_extract(mykg_path: str, scope_path: str, session: str = None) -> str:
    """Run mykg extract-graph for a scope. Returns session ID."""
    cmd = [mykg_path, "extract-graph", scope_path, "--profile", "agent-claude-code"]

    if session:
        cmd.extend(["--append", "--session", session])

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"Warning: mykg exited with code {result.returncode}")
        # Try to continue with next scope
        return session

    # Extract session ID from output if this was the first scope
    if not session:
        # Parse session from output or detect latest
        sessions_dir = Path.cwd() / "mykg_sessions"
        if not sessions_dir.exists():
            sessions_dir = Path.cwd() / ".mykg_sessions"

        if sessions_dir.exists():
            sessions = []
            for item in sessions_dir.iterdir():
                if item.is_dir():
                    try:
                        sessions.append((item.name, item.stat().st_mtime))
                    except OSError:
                        continue
            if sessions:
                sessions.sort(key=lambda x: x[1], reverse=True)
                return sessions[0][0]

    return session


def main():
    project_root = Path.cwd()
    state_dir = project_root / ".iqoqo-mykg"
    manifest_file = state_dir / "scope_manifest.json"

    if not manifest_file.exists():
        print("Error: No scope manifest found. Run scan_scope.py first.")
        print("  python3 .agents/skills/iqoqo-mykg/scripts/scan_scope.py")
        sys.exit(1)

    manifest = json.loads(manifest_file.read_text())
    scopes = manifest.get("scopes", {})

    if not scopes:
        print("No scopes to index.")
        sys.exit(0)

    mykg_path = get_mykg_path()
    # Full index always creates a fresh session (rebuild, not append)
    session = None
    print("Full index mode: creating a fresh session.")

    print(f"\nIndexing {len(scopes)} scope(s)...")
    print(f"Scopes: {', '.join(scopes.keys())}")

    # Process scopes in order
    for i, (scope_name, paths) in enumerate(scopes.items()):
        if not paths:
            print(f"\nSkipping empty scope: {scope_name}")
            continue

        # Use first path for extraction
        scope_path = paths[0]

        print(f"\n[{i+1}/{len(scopes)}] Indexing: {scope_name}")
        print(f"  Path: {scope_path}")

        if i == 0 and not session:
            # First scope - create new session
            print(f"  Mode: CREATE NEW SESSION")
            session = run_extract(mykg_path, scope_path)
            if session:
                print(f"  Created session: {session}")
            else:
                print(f"  Warning: Could not detect session ID")
        else:
            # Subsequent scope - append
            if not session:
                print(f"  Error: No session available for append. Skipping.")
                continue
            print(f"  Mode: APPEND to session {session}")
            session = run_extract(mykg_path, scope_path, session)

    # Save final session info
    if session:
        manifest["final_session"] = session
        manifest_file.write_text(json.dumps(manifest, indent=2))

    print(f"\n{'='*60}")
    print(f"Indexing complete!")
    if session:
        print(f"Session: {session}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
