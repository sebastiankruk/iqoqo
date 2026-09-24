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
"""Autonomous background daemon for processing myKG agent inbox tasks via opencode CLI.

This module implements the opencode-specific CLI adapter. All shared logic (task
discovery, payload sanitization, security guardrail injection, JSON fence
stripping, timeout negotiation, answer-envelope writing, signal handling,
worker-pool dispatch) is imported from daemon_core.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
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
    "bootstrap_opencode_auth",
    "build_combined_prompt",
    "clean_json_fences",
    "compute_effective_timeout",
    "discover_tasks",
    "is_task_done",
    "load_and_validate_task",
    "map_effort_to_variant",
    "process_task",
    "run_daemon",
    "sanitize_task_payload",
    "write_answer_envelope",
]


def map_effort_to_variant(effort: str) -> str | None:
    """Map agy-style effort levels to opencode --variant flag values.

    Mapping:
        low    -> minimal
        medium -> None (default variant, no flag)
        high   -> high
        minimal -> minimal
    """
    mapping = {
        "low": "minimal",
        "minimal": "minimal",
        "medium": None,
        "high": "high",
    }
    return mapping.get(effort.lower() if effort else "", None)


def bootstrap_opencode_auth() -> None:
    """Copy the surgically-mounted opencode auth secret into the user home directory.

    SECURITY: Credentials are copied from Docker secrets mount to user home
    because the CLI tools expect them in specific paths. We use 0o600 permissions
    and never log the credential content. The secret mount is read-only and
    isolated by the container runtime.
    """
    secret_path = Path("/run/secrets/opencode-auth.json")
    home = Path(os.environ.get("HOME", "/home/appuser"))
    target_path = home / ".local" / "share" / "opencode" / "auth.json"

    if not secret_path.is_file():
        print(
            "[opencode_daemon] Warning: secret mount /run/secrets/opencode-auth.json not found. "
            "opencode CLI will fail its own auth check if no key is available.",
            file=sys.stderr,
        )
        return

    if target_path.exists():
        return

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(secret_path.read_bytes())
        os.chmod(target_path, 0o600)
    except OSError as err:
        print(f"[opencode_daemon] Warning: failed to copy auth.json: {err}", file=sys.stderr)


def process_task(
    task_path: Path,
    outbox_dir: Path,
    model: str | None = None,
    effort: str | None = None,
    max_retries: int = 3,
) -> bool:
    """Process a single task file by calling opencode and writing the answer atomically.

    SECURITY: Uses compute_effective_timeout() which honors the task's
    timeout_seconds field and applies a hard cap (MAX_TIMEOUT_CAP) to
    prevent resource exhaustion from malicious or buggy orchestrator payloads.
    """
    task_id = task_path.stem.split(".")[0]

    if is_task_done(task_id, outbox_dir):
        return True

    for attempt in range(max_retries):
        try:
            return _execute_task(task_path, outbox_dir, model, effort, attempt)
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(
                    f"[opencode_daemon] TimeoutExpired for task {task_id}, "
                    f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait_time)
            else:
                write_error_envelope(task_id, "Subprocess timed out after all retries", outbox_dir)
                print(
                    f"[opencode_daemon] TimeoutExpired for task {task_id} "
                    f"after {max_retries} attempts",
                    file=sys.stderr,
                    flush=True,
                )
                return False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            write_error_envelope(task_id, f"Unexpected error: {type(exc).__name__}", outbox_dir)
            print(f"[opencode_daemon] Error processing task {task_id}: {type(exc).__name__}", file=sys.stderr, flush=True)
            return False

    return False


def _execute_task(
    task_path: Path,
    outbox_dir: Path,
    model: str | None,
    effort: str | None,
    attempt: int,
) -> bool:
    """Execute a single task attempt."""
    task_id = task_path.stem.split(".")[0]

    task_data = load_and_validate_task(task_path)
    if task_data is None:
        write_error_envelope(task_id, "Task validation failed: invalid or oversized task file", outbox_dir)
        return False

    actual_task_id = task_data.get("task_id", task_id)
    combined_prompt = build_combined_prompt(task_data)

    effective_model = model or os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or "opencode-go/muse-spark-1.3-contributor"
    effective_effort = effort or os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal"

    cmd = ["opencode", "run", "--auto", "--pure", "-m", effective_model]
    variant = map_effort_to_variant(effective_effort)
    if variant:
        cmd.extend(["--variant", variant])
    cmd.append(combined_prompt)

    print(
        f"[opencode_daemon] Running opencode for task {task_id[:12]} "
        f"(prompt size: {len(combined_prompt)} chars)...",
        flush=True,
    )

    # SECURITY: Compute effective timeout with hard cap to prevent DoS.
    # The task's timeout_seconds is the orchestrator's patience ceiling.
    # The dynamic formula provides a floor based on prompt size.
    effective_timeout = compute_effective_timeout(
        task_data.get("timeout_seconds"),
        len(combined_prompt),
    )

    print(f"[opencode_daemon] Using timeout: {effective_timeout}s for task {task_id[:12]}", flush=True)

    # PIPE DEADLOCK FIX: opencode's internal IPC/event-bus writes to stdout immediately
    # after 'init' (the "event connected" handshake). Using capture_output=True creates a
    # pipe whose buffer fills and blocks because subprocess.run() only drains after the
    # process exits — a classic pipe deadlock. We avoid this by redirecting stdout/stderr
    # to temp files so opencode can write freely, then read back the content after exit.
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stdout") as stdout_f,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8", suffix=".stderr") as stderr_f,
    ):

        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,  # prevent opecode from blocking on stdin
            stdout=stdout_f,
            stderr=stderr_f,
            text=True,
            encoding="utf-8",
            timeout=effective_timeout,
            check=False,
        )

        stdout_f.seek(0)
        stdout_data = stdout_f.read()
        stderr_f.seek(0)
        stderr_data = stderr_f.read()

    print(f"[opencode_daemon] opencode returned code {proc.returncode} for task {task_id[:12]}", flush=True)

    if proc.returncode != 0:
        write_error_envelope(task_id, f"Subprocess failed with exit code {proc.returncode}", outbox_dir)
        print(f"[opencode_daemon] Warning: opencode failed for {task_id}: exit code {proc.returncode}", file=sys.stderr, flush=True)
        return False

    answer_text = clean_json_fences(stdout_data)
    write_answer_envelope(task_id, answer_text, outbox_dir, actual_task_id)
    print(f"[opencode_daemon] Processed task {task_id[:12]}", flush=True)
    return True


def run_daemon(
    inbox_dir: Path,
    outbox_dir: Path,
    workers: int = 2,
    poll_interval: float = 2.0,
    model: str | None = None,
    effort: str | None = None,
) -> None:
    """Watch inbox_dir and dispatch task processing in a thread pool."""
    # Bootstrap opencode auth from secret mount
    bootstrap_opencode_auth()

    effective_model = model or os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or "opencode-go/muse-spark-1.3-contributor"
    effective_effort = effort or os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal"

    _run_daemon_core(
        inbox_dir=inbox_dir,
        outbox_dir=outbox_dir,
        process_fn=process_task,
        workers=workers,
        poll_interval=poll_interval,
        model=effective_model,
        effort=effective_effort,
        daemon_name="opencode_daemon",
    )


def main() -> None:
    """Parse CLI arguments and run daemon."""
    parser = argparse.ArgumentParser(description="Daemon for processing myKG tasks via opencode CLI.")
    parser.add_argument("inbox_dir", type=Path, help="Path to agent_inbox directory or session root")
    parser.add_argument("outbox_dir", type=Path, help="Path to agent_outbox directory or session root")
    parser.add_argument("--workers", type=int, default=2, help="Number of concurrent worker threads")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument(
        "--model",
        "-m",
        default=os.environ.get("OPENCODE_MODEL") or os.environ.get("MYKG_MODEL") or "opencode-go/muse-spark-1.3-contributor",
        help="Model to use for opencode CLI (default: opencode-go/muse-spark-1.3-contributor)",
    )
    parser.add_argument(
        "--effort",
        "-e",
        choices=["low", "medium", "high", "minimal"],
        default=os.environ.get("OPENCODE_EFFORT") or os.environ.get("MYKG_EFFORT") or "minimal",
        help="Reasoning effort for opencode CLI (default: minimal)",
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
