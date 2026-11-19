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
"""Report which LLM / vision backend actually handled requests.

Reads the ``llm_telemetry`` audit table, i.e. what really ran, not what is
configured. One row is written per LLM execution (provider, operation,
status, duration, error).

Usage::

    # inside an environment where the app can be imported (dev venv / container)
    python scripts/llm_usage_report.py --hours 24

    # against a running docker stack, from the host
    python scripts/llm_usage_report.py --docker preview --hours 24
    python scripts/llm_usage_report.py --docker prod --operation metadata_extraction

Exit codes: 0 report printed, 1 no rows in the window, 2 could not run.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ERROR_WIDTH = 70


def _find_web_container(stack: str) -> str | None:
    """Return the name of the running web container for ``stack`` (preview/prod/dev)."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    names = [n for n in result.stdout.split() if n]
    wanted = f"iqoqo-{stack}-web-" if stack != "prod" else "iqoqo-web-"
    for name in names:
        if name.startswith(wanted):
            return name
    return None


def _run_in_docker(stack: str, forwarded: list[str]) -> int:
    """Re-run this very script inside the stack's web container via stdin."""
    container = _find_web_container(stack)
    if container is None:
        print(f"No running web container found for stack '{stack}'.", file=sys.stderr)
        return 2
    source = Path(__file__).read_text(encoding="utf-8")
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "python", "-", *forwarded],
        input=source,
        text=True,
        check=False,
    )
    return proc.returncode


def _query_and_print(hours: int, operation: str | None, limit: int) -> int:
    """Query LLMTelemetry inside the active Flask app context and print summary."""
    from sqlalchemy import func, select

    from app.db import db
    from app.db.settings import LLMTelemetry

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)
    where = [LLMTelemetry.created_at >= cutoff]
    if operation:
        where.append(LLMTelemetry.operation_type == operation)

    summary = db.session.execute(
        select(
            LLMTelemetry.operation_type,
            LLMTelemetry.provider,
            LLMTelemetry.status,
            func.count(),  # pylint: disable=not-callable
            func.coalesce(func.avg(LLMTelemetry.total_duration_seconds), 0.0),
        )
        .where(*where)
        .group_by(LLMTelemetry.operation_type, LLMTelemetry.provider, LLMTelemetry.status)
        .order_by(LLMTelemetry.operation_type, LLMTelemetry.provider, LLMTelemetry.status)
    ).all()

    rows = db.session.execute(select(LLMTelemetry).where(*where).order_by(LLMTelemetry.created_at.desc()).limit(limit)).scalars().all()

    scope = f"operation={operation}" if operation else "all operations"
    print(f"LLM usage, last {hours}h ({scope}), UTC now {datetime.now(UTC):%Y-%m-%d %H:%M}")
    print("=" * 78)
    if not summary:
        print("No llm_telemetry rows in this window.")
        print("Either nothing ran, or the backend that ran does not record telemetry.")
        return 1

    print(f"{'operation':<22}{'provider':<12}{'status':<13}{'count':>6}{'avg s':>9}")
    for op, provider, status, count, avg in summary:
        print(f"{op:<22}{provider:<12}{status:<13}{count:>6}{avg:>9.1f}")

    print()
    print(f"Latest {len(rows)} executions (newest first)")
    print("-" * 78)
    for row in rows:
        error = (row.error_message or "").replace("\n", " ")
        if len(error) > ERROR_WIDTH:
            error = error[: ERROR_WIDTH - 1] + "…"
        print(
            f"{row.created_at:%m-%d %H:%M:%S}  {row.provider:<10} {row.operation_type:<20} "
            f"{row.status:<9} {row.total_duration_seconds or 0:>6.1f}s  {error}"
        )
    return 0


def _report(hours: int, operation: str | None, limit: int) -> int:
    """Print the telemetry report for the last ``hours`` hours."""
    from flask import has_app_context
    from sqlalchemy.exc import SQLAlchemyError

    try:
        if has_app_context():
            return _query_and_print(hours, operation, limit)

        from app import create_app

        app = create_app()
        with app.app_context():
            return _query_and_print(hours, operation, limit)
    except (SQLAlchemyError, OSError, RuntimeError, ValueError) as exc:
        print(f"Could not read llm_telemetry: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Report LLM / vision backends that actually ran.")
    parser.add_argument("--hours", type=int, default=24, help="Look-back window in hours (default 24).")
    parser.add_argument("--operation", default=None, help="Filter, e.g. metadata_extraction or cover_generation.")
    parser.add_argument("--limit", type=int, default=25, help="Max individual rows to list (default 25).")
    parser.add_argument("--docker", metavar="STACK", default=None, help="Run inside a docker stack: dev|preview|prod.")
    args = parser.parse_args(argv)

    if args.docker:
        forwarded = ["--hours", str(args.hours), "--limit", str(args.limit)]
        if args.operation:
            forwarded += ["--operation", args.operation]
        try:
            return _run_in_docker(args.docker, forwarded)
        except OSError as exc:
            print(f"Could not run report inside docker '{args.docker}': {exc}", file=sys.stderr)
            return 2

    try:
        return _report(args.hours, args.operation, args.limit)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Could not read llm_telemetry: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
