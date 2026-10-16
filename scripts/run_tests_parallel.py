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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Execute test suite across 4 parallel streams (Domain, API, Frontend, Tooling)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = Path(sys.executable).parent
AI_MODE = os.environ.get("IQOQO_AI_MODE") == "1"

# Patterns defining Stream 1 (FRBR & Domain Core)
DOMAIN_PATTERNS: tuple[str, ...] = (
    "frbr",
    "iri",
    "duplicate",
    "entity",
    "item",
    "work",
    "expression",
    "manifestation",
    "model",
    "db_",
    "migration",
    "ontology",
    "contribution",
    "lod",
)

# Patterns defining Stream 2 (API, Auth & Federation)
API_PATTERNS: tuple[str, ...] = (
    "api",
    "auth",
    "profile",
    "account",
    "federation",
    "sparql",
    "public",
    "sharing",
    "social",
    "admin",
    "search",
    "lending",
    "roadmap",
    "wishlist",
    "user",
    "rate_",
)


def get_all_test_files() -> list[str]:
    """Discover all root test_*.py test files."""
    test_dir = ROOT / "tests"
    return sorted(p.name for p in test_dir.glob("test_*.py"))


def partition_backend_tests() -> tuple[list[str], list[str], list[str]]:
    """Partition all backend test files into 3 distinct non-overlapping streams.

    Returns:
        (domain_files, api_files, tooling_files)
    """
    all_files = get_all_test_files()
    stream_domain: list[str] = []
    stream_api: list[str] = []
    stream_tooling: list[str] = []

    for name in all_files:
        name_lower = name.lower()
        if any(pat in name_lower for pat in DOMAIN_PATTERNS):
            stream_domain.append(f"tests/{name}")
        elif any(pat in name_lower for pat in API_PATTERNS):
            stream_api.append(f"tests/{name}")
        else:
            stream_tooling.append(f"tests/{name}")

    return stream_domain, stream_api, stream_tooling


def tool(name: str) -> str:
    """Resolve executable from current venv or system PATH."""
    candidate = VENV_BIN / name
    return str(candidate) if candidate.exists() else name


def run_stream(
    stream_id: str,
    title: str,
    commands: list[list[str]],
    cwd: Path = ROOT,
) -> tuple[str, bool, float, str]:
    """Execute one stream's commands sequentially, measuring elapsed time.

    Returns:
        (stream_id, success, elapsed_seconds, output)
    """
    start_time = time.time()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)

    combined_output: list[str] = []
    for cmd in commands:
        if not AI_MODE:
            print(f"[{stream_id}] Running: {' '.join(cmd)}")
        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            out = (res.stdout or "") + (res.stderr or "")
            combined_output.append(out)
            if res.returncode != 0:
                elapsed = time.time() - start_time
                return stream_id, False, elapsed, "\n".join(combined_output)
        except Exception as exc:
            elapsed = time.time() - start_time
            return stream_id, False, elapsed, f"Exception executing {cmd}: {exc}"

    elapsed = time.time() - start_time
    return stream_id, True, elapsed, "\n".join(combined_output)


def build_stream_definitions() -> dict[str, dict]:
    """Construct command definitions for all 4 parallel test streams."""
    domain_files, api_files, tooling_files = partition_backend_tests()
    pytest_bin = tool("pytest")

    pytest_args = ["-q", "--tb=short", "--no-header"] if AI_MODE else ["-v"]

    # Stream 1: Domain & FRBR Core
    stream_domain = {
        "title": "Stream 1 — FRBR, Ontology & Domain Core",
        "commands": [[pytest_bin] + pytest_args + domain_files],
        "cwd": ROOT,
        "files_count": len(domain_files),
    }

    # Stream 2: API, Auth, Social & Federation
    stream_api = {
        "title": "Stream 2 — API, Auth & Federation",
        "commands": [[pytest_bin] + pytest_args + api_files],
        "cwd": ROOT,
        "files_count": len(api_files),
    }

    # Stream 3: Frontend Vitest Unit Tests
    npm_cmd = "npm"
    vitest_cmd = [npm_cmd, "run", "test"]
    if AI_MODE:
        vitest_cmd.extend(["--", "--reporter=dot"])
    stream_frontend = {
        "title": "Stream 3 — Frontend Unit Suite (Vitest)",
        "commands": [vitest_cmd],
        "cwd": ROOT / "frontend",
        "files_count": "frontend",
    }

    # Stream 4: Tooling, Services, ETL, Telemetry & BATS
    bats_cmd = ["bats", "tests/bash/"] if Path("/usr/bin/bats").exists() or Path("/usr/local/bin/bats").exists() else None
    if not bats_cmd and (ROOT / "node_modules/.bin/bats").exists():
        bats_cmd = [str(ROOT / "node_modules/.bin/bats"), "tests/bash/"]

    tooling_cmds = [[pytest_bin] + pytest_args + tooling_files]
    if bats_cmd:
        tooling_cmds.append(bats_cmd)

    stream_tooling = {
        "title": "Stream 4 — Services, Tooling, Scripts & BATS",
        "commands": tooling_cmds,
        "cwd": ROOT,
        "files_count": len(tooling_files),
    }

    return {
        "domain": stream_domain,
        "api": stream_api,
        "frontend": stream_frontend,
        "tooling": stream_tooling,
    }


def main() -> int:
    """CLI entry point for running tests across 4 parallel streams."""
    parser = argparse.ArgumentParser(description="Run iqoqo test suite in 4 parallel streams.")
    parser.add_argument(
        "--stream",
        choices=["domain", "api", "frontend", "tooling"],
        help="Run only one specific test stream",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List file partitions across streams and exit",
    )
    args = parser.parse_args()

    streams = build_stream_definitions()

    if args.list:
        print("4 Parallel Test Streams Partition:")
        for stream_id, meta in streams.items():
            print(f"  [{stream_id}] {meta['title']} ({meta['files_count']} test files/targets)")
        return 0

    target_streams = [args.stream] if args.stream else list(streams.keys())

    print("=" * 60)
    print(f"Starting {len(target_streams)} Test Stream(s) in Parallel")
    for s in target_streams:
        print(f"  * [{s}] {streams[s]['title']}")
    print("=" * 60)

    start_total = time.time()
    results: dict[str, tuple[bool, float, str]] = {}

    with ThreadPoolExecutor(max_workers=len(target_streams)) as executor:
        future_map = {
            executor.submit(
                run_stream,
                stream_id,
                streams[stream_id]["title"],
                streams[stream_id]["commands"],
                streams[stream_id]["cwd"],
            ): stream_id
            for stream_id in target_streams
        }

        for future in as_completed(future_map):
            stream_id = future_map[future]
            try:
                sid, success, elapsed, output = future.result()
                results[sid] = (success, elapsed, output)
                status_str = "PASSED" if success else "FAILED"
                print(f"[{sid}] {status_str} in {elapsed:.2f}s")
            except Exception as exc:
                results[stream_id] = (False, 0.0, str(exc))
                print(f"[{stream_id}] ERROR: {exc}")

    total_elapsed = time.time() - start_total
    all_passed = all(success for success, _, _ in results.values())

    print("\n" + "=" * 60)
    print(f"Parallel Test Execution Summary ({total_elapsed:.2f}s total)")
    print("=" * 60)
    for sid in target_streams:
        success, elapsed, output = results[sid]
        status_label = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status_label:<8} [{sid:<8}] {elapsed:>6.2f}s — {streams[sid]['title']}")
        if not success:
            print("-" * 60)
            print(f"Failure log for [{sid}]:")
            # Print trailing 25 lines of failure output
            lines = [line for line in output.splitlines() if line.strip()]
            for line in lines[-25:]:
                print(f"  {line}")
            print("-" * 60)

    print("=" * 60)
    if all_passed:
        print(f"All {len(target_streams)} test streams passed successfully!")
        return 0
    print("One or more test streams failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
