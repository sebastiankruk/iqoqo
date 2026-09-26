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
"""Autonomous background daemon for processing myKG agent inbox tasks via Antigravity CLI.

This module implements the agy-specific CLI adapter. All shared logic (task
discovery, payload sanitization, security guardrail injection, JSON fence
stripping, timeout negotiation, answer-envelope writing, signal handling,
worker-pool dispatch) is imported from daemon_core.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Import shared core from the same directory
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from daemon_core import (  # noqa: E402
    REDACTED_PATTERNS,
    SECURITY_GUARDRAIL,
    build_combined_prompt,
    clean_json_fences,
    compute_effective_timeout,
    discover_tasks,
    is_task_done,
    load_and_validate_task,
    run_daemon as _run_daemon_core,
    sanitize_task_payload,
    write_answer_envelope,
    write_error_envelope,
)

# Re-export shared symbols for backward-compatible test access
__all__ = [
    "REDACTED_PATTERNS",
    "SECURITY_GUARDRAIL",
    "build_combined_prompt",
    "clean_json_fences",
    "compute_effective_timeout",
    "discover_tasks",
    "is_task_done",
    "load_and_validate_task",
    "process_task",
    "run_daemon",
    "sanitize_task_payload",
    "write_answer_envelope",
]


def process_task(
    task_path: Path,
    outbox_dir: Path,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> bool:
    """Process a single task file by calling agy and writing the answer atomically.

    SECURITY: Uses compute_effective_timeout() which honors the task's
    timeout_seconds field and applies a hard cap (MAX_TIMEOUT_CAP) to
    prevent resource exhaustion from malicious or buggy orchestrator payloads.
    """
    task_id = task_path.stem.split(".")[0]

    if is_task_done(task_id, outbox_dir):
        return True

    try:
        task_data = load_and_validate_task(task_path)
        if task_data is None:
            write_error_envelope(task_id, "Task validation failed: invalid or oversized task file", outbox_dir)
            return False

        actual_task_id = task_data.get("task_id", task_id)
        combined_prompt = build_combined_prompt(task_data)

        effective_model = model or os.environ.get("MYKG_MODEL") or os.environ.get("AGY_MODEL") or "gemini-3.8-flash-low"
        effective_effort = effort or os.environ.get("MYKG_EFFORT") or os.environ.get("AGY_EFFORT") or "low"

        # SECURITY: Compute effective timeout with hard cap to prevent DoS
        effective_timeout = compute_effective_timeout(
            task_data.get("timeout_seconds"),
            len(combined_prompt),
        )

        # SECURITY: --dangerously-skip-permissions bypasses LLM safety controls.
        # This is required for unattended daemon operation, but increases risk if
        # the container is not properly isolated. Ensure:
        # 1. Container has no network access (except to LLM API endpoints)
        # 2. Container runs as non-root user
        # 3. Filesystem is read-only except for inbox/outbox directories
        cmd = ["agy", "--dangerously-skip-permissions", "-p", combined_prompt]
        if effective_model:
            cmd.extend(["--model", effective_model])
        if effective_effort:
            cmd.extend(["--effort", effective_effort])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=effective_timeout,
            check=False,
        )

        if proc.returncode != 0:
            error_msg = f"Subprocess failed with exit code {proc.returncode}"
            write_error_envelope(task_id, error_msg, outbox_dir)
            print(f"[agy_daemon] Warning: agy failed for {task_id}: exit code {proc.returncode}", file=sys.stderr)
            return False

        answer_text = clean_json_fences(proc.stdout)
        write_answer_envelope(task_id, answer_text, outbox_dir, actual_task_id)
        print(f"[agy_daemon] Processed task {task_id[:12]}")
        return True
    except subprocess.TimeoutExpired:
        write_error_envelope(task_id, "Subprocess timed out", outbox_dir)
        print(f"[agy_daemon] TimeoutExpired for task {task_id}", file=sys.stderr)
        return False
    except Exception as exc:  # pylint: disable=broad-exception-caught
        write_error_envelope(task_id, f"Unexpected error: {type(exc).__name__}", outbox_dir)
        print(f"[agy_daemon] Error processing task {task_id}: {type(exc).__name__}", file=sys.stderr)
        return False


def run_daemon(
    inbox_dir: Path,
    outbox_dir: Path,
    workers: int = 2,
    poll_interval: float = 2.0,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> None:
    """Watch inbox_dir and dispatch task processing in a thread pool."""
    effective_model = model or os.environ.get("MYKG_MODEL") or os.environ.get("AGY_MODEL") or "gemini-3.8-flash-low"
    effective_effort = effort or os.environ.get("MYKG_EFFORT") or os.environ.get("AGY_EFFORT") or "low"

    # SECURITY: Credentials are copied from Docker secrets mount to user home
    # because the CLI tools expect them in specific paths. We use 0o600 permissions
    # and never log the credential content. The secret mount is read-only and
    # isolated by the container runtime.
    secret_token = Path("/run/secrets/antigravity-oauth-token")
    target_token_dir = Path(os.environ.get("HOME", "/home/appuser")) / ".gemini" / "antigravity-cli"
    if secret_token.is_file() and not (target_token_dir / "antigravity-oauth-token").exists():
        try:
            target_token_dir.mkdir(parents=True, exist_ok=True)
            (target_token_dir / "antigravity-oauth-token").write_bytes(secret_token.read_bytes())
            os.chmod(target_token_dir / "antigravity-oauth-token", 0o600)
        except OSError as err:
            print(f"[agy_daemon] Warning: failed to copy oauth token: {err}", file=sys.stderr)

    _run_daemon_core(
        inbox_dir=inbox_dir,
        outbox_dir=outbox_dir,
        process_fn=process_task,
        workers=workers,
        poll_interval=poll_interval,
        model=effective_model,
        effort=effective_effort,
        daemon_name="agy_daemon",
    )


def main() -> None:
    """Parse CLI arguments and run daemon."""
    parser = argparse.ArgumentParser(description="Daemon for processing myKG tasks via Antigravity CLI.")
    parser.add_argument("inbox_dir", type=Path, help="Path to agent_inbox directory or session root")
    parser.add_argument("outbox_dir", type=Path, help="Path to agent_outbox directory or session root")
    parser.add_argument("--workers", type=int, default=2, help="Number of concurrent worker threads")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument(
        "--model",
        "-m",
        default=os.environ.get("MYKG_MODEL") or os.environ.get("AGY_MODEL") or "gemini-3.8-flash-low",
        help="Model to use for agy CLI (default: gemini-3.8-flash-low)",
    )
    parser.add_argument(
        "--effort",
        "-e",
        choices=["low", "medium", "high"],
        default=os.environ.get("MYKG_EFFORT") or os.environ.get("AGY_EFFORT") or "low",
        help="Reasoning effort for agy CLI (default: low)",
    )

    args = parser.parse_args()
    run_daemon(
        inbox_dir=args.inbox_dir,
        outbox_dir=args.outbox_dir,
        workers=args.workers,
        poll_interval=args.poll_interval,
        model=args.model,
        effort=args.effort,
    )


if __name__ == "__main__":
    main()
