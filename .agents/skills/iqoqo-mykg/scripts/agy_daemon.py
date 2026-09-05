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
"""Autonomous background daemon for processing myKG agent inbox tasks via Antigravity CLI."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional, Set


def clean_json_fences(raw_text: str) -> str:
    """Strip markdown code fences and extraneous leading/trailing whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def process_task(
    task_path: Path,
    outbox_dir: Path,
    timeout: int = 300,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> bool:
    """Process a single task file by calling agy and writing the answer atomically."""
    task_id = task_path.stem.split(".")[0]
    done_file = outbox_dir / f"{task_id}.done"
    answer_file = outbox_dir / f"{task_id}.answer.json"
    temp_file = outbox_dir / f"{task_id}.answer.json.tmp"

    if done_file.exists() and answer_file.exists():
        return True

    try:
        task_data: Dict[str, Any] = json.loads(task_path.read_text(encoding="utf-8"))
        actual_task_id = task_data.get("task_id", task_id)
        system_prompt = task_data.get("system", "")
        user_prompt = task_data.get("user", "")

        combined_prompt = (
            f"System Instructions:\n{system_prompt}\n\n"
            f"User Prompt:\n{user_prompt}\n\n"
            "CRITICAL: Respond ONLY with the requested JSON payload. "
            "Do NOT include conversational text or markdown code fences."
        )

        effective_model = model or os.environ.get("MYKG_MODEL") or os.environ.get("AGY_MODEL") or "gemini-3.8-flash-low"
        effective_effort = effort or os.environ.get("MYKG_EFFORT") or os.environ.get("AGY_EFFORT") or "low"

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
            timeout=timeout,
            check=False,
        )

        if proc.returncode != 0:
            print(f"[agy_daemon] Warning: agy failed for {task_id}: {proc.stderr}", file=sys.stderr)
            return False

        answer_text = clean_json_fences(proc.stdout)
        answer_envelope = {
            "task_id": actual_task_id,
            "answer": answer_text,
        }

        temp_file.write_text(json.dumps(answer_envelope), encoding="utf-8")
        temp_file.rename(answer_file)
        done_file.touch()
        print(f"[agy_daemon] Processed task {task_id[:12]}")
        return True
    except subprocess.TimeoutExpired:
        print(f"[agy_daemon] TimeoutExpired for task {task_id}", file=sys.stderr)
        return False
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"[agy_daemon] Error processing task {task_id}: {exc}", file=sys.stderr)
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
    inbox_dir.mkdir(parents=True, exist_ok=True)
    outbox_dir.mkdir(parents=True, exist_ok=True)

    running: bool = True

    def handle_signal(_signum: int, _frame: Any) -> None:
        nonlocal running
        print("[agy_daemon] Received stop signal, shutting down...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    active_futures: Dict[Future[bool], str] = {}
    submitted_tasks: Set[str] = set()

    effective_model = model or os.environ.get("MYKG_MODEL") or os.environ.get("AGY_MODEL") or "gemini-3.8-flash-low"
    effective_effort = effort or os.environ.get("MYKG_EFFORT") or os.environ.get("AGY_EFFORT") or "low"
    config_desc = []
    if effective_model:
        config_desc.append(f"model={effective_model}")
    if effective_effort:
        config_desc.append(f"effort={effective_effort}")
    config_str = f" ({', '.join(config_desc)})" if config_desc else ""

    # Bootstrap OAuth token into user home if mounted from secret location
    secret_token = Path("/run/secrets/antigravity-oauth-token")
    target_token_dir = Path(os.environ.get("HOME", "/home/appuser")) / ".gemini" / "antigravity-cli"
    if secret_token.is_file() and not (target_token_dir / "antigravity-oauth-token").exists():
        try:
            target_token_dir.mkdir(parents=True, exist_ok=True)
            (target_token_dir / "antigravity-oauth-token").write_bytes(secret_token.read_bytes())
            os.chmod(target_token_dir / "antigravity-oauth-token", 0o600)
        except OSError as err:
            print(f"[agy_daemon] Warning: failed to copy oauth token: {err}", file=sys.stderr)

    print(f"[agy_daemon] Starting daemon watching {inbox_dir} (workers={workers}){config_str}...")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while running:
            # Clean completed futures
            done_futures = [f for f in active_futures if f.done()]
            for f in done_futures:
                tid = active_futures.pop(f)
                submitted_tasks.discard(tid)

            # Discover new pending tasks
            try:
                task_files = list(inbox_dir.glob("*.task.json"))
                if not task_files and (inbox_dir / "intermediate" / "agent_inbox").exists():
                    task_files = list((inbox_dir / "intermediate" / "agent_inbox").glob("*.task.json"))
                if not task_files:
                    task_files = list(inbox_dir.glob("*/intermediate/agent_inbox/*.task.json"))
            except OSError:
                task_files = []

            for task_file in task_files:
                task_id = task_file.stem.split(".")[0]
                # Determine associated outbox
                if task_file.parent.name == "agent_inbox":
                    target_outbox = task_file.parent.parent / "agent_outbox"
                else:
                    target_outbox = outbox_dir
                target_outbox.mkdir(parents=True, exist_ok=True)
                done_marker = target_outbox / f"{task_id}.done"

                if not done_marker.exists() and task_id not in submitted_tasks:
                    submitted_tasks.add(task_id)
                    fut = executor.submit(
                        process_task,
                        task_file,
                        target_outbox,
                        300,
                        effective_model,
                        effective_effort,
                    )
                    active_futures[fut] = task_id

            time.sleep(poll_interval)


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
