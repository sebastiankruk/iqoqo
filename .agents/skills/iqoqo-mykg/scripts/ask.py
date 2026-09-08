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
"""Session-agnostic query tool for myKG knowledge graph."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_mykg_bin() -> str:
    """Find mykg executable."""
    venv_bin = Path.cwd() / ".venv" / "bin" / "mykg"
    if venv_bin.exists():
        return str(venv_bin)
    which_bin = shutil.which("mykg")
    if which_bin:
        return which_bin
    return "mykg"


def get_latest_session(project_root: Path) -> str | None:
    """Find the most recent mykg session directory."""
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


def main() -> None:
    """Entry point for ask.py."""
    parser = argparse.ArgumentParser(description="Query the latest myKG knowledge graph session")
    parser.add_argument("question", nargs="+", help="Question or concept keyword to query")
    parser.add_argument("--mode", choices=["bfs", "dfs"], default="bfs", help="Graph traversal mode (default: bfs)")
    parser.add_argument("--depth", type=int, default=2, help="Graph traversal depth limit (default: 2)")
    parser.add_argument("--token-budget", type=int, default=3000, help="Token budget for context (default: 3000)")
    parser.add_argument("--session", help="Explicit session name override")
    args = parser.parse_args()

    project_root = Path.cwd()
    mykg_bin = find_mykg_bin()

    session_name = args.session or get_latest_session(project_root)
    if not session_name:
        print("Error: No myKG session found in mykg_sessions/ or .mykg_sessions/.", file=sys.stderr)
        print("Run 'IQOQO_AI_MODE=1 make mykg-index' to build the initial knowledge graph.", file=sys.stderr)
        sys.exit(1)

    question_text = " ".join(args.question)
    cmd = [
        mykg_bin,
        "query",
        question_text,
        "--session",
        session_name,
        "--mode",
        args.mode,
        "--depth",
        str(args.depth),
        "--token-budget",
        str(args.token_budget),
    ]

    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
