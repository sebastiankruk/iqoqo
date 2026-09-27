#!/usr/bin/env python3
"""Screen the catalog for duplicate FRBR Works and Manifestations.

Heuristic blocking narrows the catalog to plausible pairs, then a local Ollama
model scores each surviving pair.  The script only ever *queues* candidates for
administrative review; merging is a separate, explicitly reviewed action.

Ollama health (and the presence of the configured model) is verified before any
pair is evaluated, so a missing prerequisite is reported as an actionable setup
message instead of a stream of per-pair inference failures.  The default mode
is a dry run: add ``--apply`` to persist candidate rows.
"""

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

import argparse
import os
import sys
from typing import Any

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from app import create_app
from app.core import duplicate_service
from app.core.duplicate_service import DEFAULT_THRESHOLD, TIER_ALL, DetectionReport, DuplicateServiceError

#: Exit code used for usage/argument errors, mirroring ``backfill_legacy_covers.py``.
EXIT_PREREQUISITE = 2
EXIT_FAILED = 1
EXIT_OK = 0

#: Fields printed one per line, in a stable order, for operator-friendly summaries.
_SUMMARY_FIELDS: tuple[str, ...] = (
    "entities_screened",
    "candidate_pairs",
    "work_candidates",
    "manifestation_candidates",
    "llm_evaluations",
    "llm_failures",
    "below_threshold",
    "already_known",
    "created",
    "would_create",
)


def _format_report(report: DetectionReport) -> str:
    """Render a detection report as a credential-free summary string.

    Args:
        report: Report returned by the detection run.

    Returns:
        Single-line ``key=value`` summary.
    """
    return ", ".join(f"{name}={getattr(report, name)}" for name in _SUMMARY_FIELDS)


def run_scan(
    *,
    app: Any = None,
    tier: str = TIER_ALL,
    threshold: float = DEFAULT_THRESHOLD,
    limit: int | None = None,
    dry_run: bool = True,
    skip_health_check: bool = False,
    progress: Any = print,
) -> DetectionReport:
    """Verify prerequisites and run one detection pass.

    Args:
        app: Optional pre-built Flask application, used by tests.
        tier: ``"work"``, ``"manifestation"``, or ``"all"``.
        threshold: Minimum LLM confidence required to queue a candidate.
        limit: Maximum number of catalog entities to load per tier, or ``None``.
        dry_run: Evaluate and report without writing candidate rows.
        skip_health_check: Bypass the Ollama probe.  Intended for unit tests and
            for triage runs where local inference is known to be offline.
        progress: Callable receiving human-readable progress lines.

    Returns:
        The :class:`DetectionReport` describing the run.

    Raises:
        DuplicateServiceError: If a prerequisite is missing or an argument is
            invalid.  Callers turn this into a non-zero exit code.
    """
    if not skip_health_check:
        healthy, message = duplicate_service.check_ollama_health()
        if not healthy:
            # The health message already ends in a period, so strip it before
            # appending the remediation hint.
            raise DuplicateServiceError(
                f"{message.rstrip('.')}. Run 'ollama pull {duplicate_service.ollama_model()}' "
                "or set OLLAMA_DEDUPE_MODEL to an installed model"
            )

    flask_app = app or create_app()
    with flask_app.app_context():
        report = duplicate_service.run_detection(
            tier=tier,
            threshold=threshold,
            limit=limit,
            dry_run=dry_run,
            progress=progress,
        )
    return report


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the duplicate detection CLI."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--tier",
        choices=sorted((duplicate_service.TIER_WORK, duplicate_service.TIER_MANIFESTATION, TIER_ALL)),
        default=TIER_ALL,
        help="Entity tier to screen (default: %(default)s)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum LLM confidence required to queue a candidate, 0.0-1.0 (default: %(default)s)",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of catalog entities to load per tier")
    parser.add_argument("--apply", action="store_true", help="Persist candidate rows; dry-run is the default")
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip the Ollama probe and let per-pair inference failures be reported instead",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress per-page progress lines")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the duplicate detection CLI.

    Args:
        argv: Argument list, defaulting to :data:`sys.argv`.

    Returns:
        ``0`` on success, ``2`` for a missing prerequisite or invalid argument,
        and ``1`` for any other failure.  Internal exception detail is never
        printed, to avoid leaking connection strings or catalog content.
    """
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply
    progress = None if args.quiet else print

    print(f"Tier: {args.tier}")
    print(f"Threshold: {args.threshold}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")

    try:
        report = run_scan(
            tier=args.tier,
            threshold=args.threshold,
            limit=args.limit,
            dry_run=dry_run,
            skip_health_check=args.skip_health_check,
            progress=progress,
        )
    except DuplicateServiceError as exc:
        print(f"Detection not started: {exc}", file=sys.stderr)
        return EXIT_PREREQUISITE
    except Exception as exc:  # Do not expose connection strings or catalog content in tracebacks.
        print(f"Detection aborted: {type(exc).__name__}", file=sys.stderr)
        return EXIT_FAILED

    print("Summary: " + _format_report(report))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
