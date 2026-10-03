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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Re-queue mykg agent tasks that previously failed, so inference is retried.

Why this exists
---------------
``daemon_core.is_task_done()`` treats an ``.error`` envelope as terminal, and
``write_error_envelope()`` is first-error-wins (it refuses to overwrite an
existing ``.error``). Together those make a single failed run *permanent*: the
task is never retried, and neither ``mykg-update`` nor a full ``mykg-index``
will pick it up again, because both consult the same per-task gate. Meanwhile
the runner still exits 0 and reports "N/N scopes updated", so the damage is
silent — the knowledge graph just quietly stops containing those extractions.

That is exactly the wrong behaviour for a *transient* failure (a bad model
name, a revoked variant, a network blip, a rate limit). The fix is to clear the
error marker and let the daemon re-run those tasks. The task payloads live in
the inbox and are not consumed, so nothing needs to be re-derived from source.

What it does
------------
Moves ``<task_id>.error`` envelopes out of the agent outbox into a quarantine
directory inside the session, which flips those tasks back to "not done". The
next daemon run re-processes them.

By default envelopes are *quarantined, not deleted*, so a reset is reversible
and auditable. Use ``--purge`` to discard them outright.

Examples
--------
    python3 retry_failed.py --dry-run          # report only, change nothing
    python3 retry_failed.py                    # re-queue failures, newest session
    python3 retry_failed.py --session 2026-08-27T20-53-32
    python3 retry_failed.py --purge            # discard instead of quarantine
"""

import argparse
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ERROR_SUFFIX = ".error"
ANSWER_SUFFIX = ".answer.json"
DONE_SUFFIX = ".done"
TASK_SUFFIX = ".task.json"
QUARANTINE_DIRNAME = "failed_envelopes"


def find_session(project_root: Path, session: str | None) -> tuple[str | None, Path | None]:
    """Resolve the target session. Returns (name, path).

    Mirrors mykg_sync.sh: prefer mykg_sessions/, fall back to .mykg_sessions/
    only when the former is absent, and treat the newest directory by mtime as
    "latest".

    NOTE: a symlinked mykg_sessions/ is valid and must be followed. The
    sessions directory here points at a Dropbox folder, so testing
    ``is_symlink()`` and then abandoning the path would leave us with nothing.
    """
    primary = project_root / "mykg_sessions"
    sessions_dir = primary if primary.exists() else project_root / ".mykg_sessions"

    if not sessions_dir.exists():
        return None, None

    if session:
        candidate = sessions_dir / session
        return (session, candidate) if candidate.is_dir() else (None, None)

    newest: tuple[float, Path] | None = None
    for item in sessions_dir.iterdir():
        if not item.is_dir():
            continue
        try:
            mtime = item.stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest[0]:
            newest = (mtime, item)

    return (newest[1].name, newest[1]) if newest else (None, None)


def classify(outbox: Path, inbox: Path) -> dict[str, list[str]]:
    """Bucket error envelopes by whether the task can actually be retried."""
    buckets = {
        "retryable": [],  # failed and still has its task payload
        "already_answered": [],  # has a good answer; the error is stale noise
        "orphaned": [],  # failed, but the task payload is gone
    }

    for envelope in sorted(outbox.glob(f"*{ERROR_SUFFIX}")):
        task_id = envelope.name[: -len(ERROR_SUFFIX)]
        if (outbox / f"{task_id}{ANSWER_SUFFIX}").exists():
            buckets["already_answered"].append(task_id)
        elif (inbox / f"{task_id}{TASK_SUFFIX}").exists():
            buckets["retryable"].append(task_id)
        else:
            buckets["orphaned"].append(task_id)

    return buckets


def quarantine(outbox: Path, task_ids: list[str], destination: Path) -> int:
    """Move error envelopes into the quarantine dir. Returns files moved."""
    destination.mkdir(parents=True, exist_ok=True)
    moved = 0
    for task_id in task_ids:
        source = outbox / f"{task_id}{ERROR_SUFFIX}"
        try:
            shutil.move(str(source), str(destination / source.name))
            moved += 1
        except OSError as err:
            print(f"  ! could not move {task_id}: {err}", file=sys.stderr)
    return moved


def purge(outbox: Path, task_ids: list[str]) -> int:
    """Delete error envelopes outright. Returns files removed."""
    removed = 0
    for task_id in task_ids:
        try:
            (outbox / f"{task_id}{ERROR_SUFFIX}").unlink()
            removed += 1
        except OSError as err:
            print(f"  ! could not delete {task_id}: {err}", file=sys.stderr)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-queue failed mykg agent tasks for inference retry.")
    parser.add_argument("--session", help="Session name (default: newest by mtime)")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true", help="Report only; change nothing")
    parser.add_argument("--purge", action="store_true", help="Delete error envelopes instead of quarantining them")
    args = parser.parse_args()

    name, session_path = find_session(args.project_root, args.session)
    if session_path is None:
        target = f"'{args.session}'" if args.session else "any session"
        print(f"retry_failed: no mykg session found for {target}.", file=sys.stderr)
        return 1

    intermediate = session_path / "intermediate"
    inbox = intermediate / "agent_inbox"
    outbox = intermediate / "agent_outbox"

    if not outbox.is_dir():
        print(f"retry_failed: {outbox} does not exist; nothing to retry.", file=sys.stderr)
        return 1

    buckets = classify(outbox, inbox)
    total = sum(len(v) for v in buckets.values())

    print(f"Session: {name}")
    print(f"Outbox:   {outbox}")
    print()
    print(f"  error envelopes total      : {total}")
    print(f"  retryable (task in inbox) : {len(buckets['retryable'])}")
    print(f"  already answered (stale)   : {len(buckets['already_answered'])}")
    print(f"  orphaned (no task payload): {len(buckets['orphaned'])}")

    if not total:
        print("\nNothing to retry.")
        return 0

    if args.dry_run:
        print("\nDry run: no files changed.")
        return 0

    # Only retryable tasks are cleared. Stale errors on already-answered tasks
    # are left alone so the record of what happened is not rewritten, and
    # orphans are left alone because clearing them would change nothing.
    targets = buckets["retryable"]
    if not targets:
        print("\nNo retryable tasks; nothing changed.")
        return 0

    if args.purge:
        removed = purge(outbox, targets)
        print(f"\nPurged {removed} error envelope(s). Those tasks will retry on the next run.")
    else:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        destination = intermediate / QUARANTINE_DIRNAME / stamp
        moved = quarantine(outbox, targets, destination)
        print(f"\nRe-queued {moved} task(s). Their error envelopes are in:")
        print(f"  {destination}")
        print("  (restore with: mv <that dir>/*.error <outbox>/)")

    print("\nNext step: fix the underlying failure, then re-run:")
    print("  make mykg-update AI_AGENT=<agy|opencode>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
