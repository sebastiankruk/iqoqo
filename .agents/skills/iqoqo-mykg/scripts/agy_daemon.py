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
from typing import Any, Dict, Set


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


def process_task(task_path: Path, outbox_dir: Path, timeout: int = 300) -> bool:
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

        proc = subprocess.run(
            ["agy", "--dangerously-skip-permissions", "-p", combined_prompt],
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


def run_daemon(inbox_dir: Path, outbox_dir: Path, workers: int = 2, poll_interval: float = 2.0) -> None:
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

    print(f"[agy_daemon] Starting daemon watching {inbox_dir} (workers={workers})...")

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
            except OSError:
                task_files = []

            for task_file in task_files:
                task_id = task_file.stem.split(".")[0]
                done_marker = outbox_dir / f"{task_id}.done"

                if not done_marker.exists() and task_id not in submitted_tasks:
                    submitted_tasks.add(task_id)
                    fut = executor.submit(process_task, task_file, outbox_dir)
                    active_futures[fut] = task_id

            time.sleep(poll_interval)


def main() -> None:
    """Parse CLI arguments and run daemon."""
    parser = argparse.ArgumentParser(description="Daemon for processing myKG tasks via Antigravity CLI.")
    parser.add_argument("inbox_dir", type=Path, help="Path to agent_inbox directory")
    parser.add_argument("outbox_dir", type=Path, help="Path to agent_outbox directory")
    parser.add_argument("--workers", type=int, default=2, help="Number of concurrent worker threads")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")

    args = parser.parse_args()
    run_daemon(
        inbox_dir=args.inbox_dir,
        outbox_dir=args.outbox_dir,
        workers=args.workers,
        poll_interval=args.poll_interval,
    )


if __name__ == "__main__":
    main()
