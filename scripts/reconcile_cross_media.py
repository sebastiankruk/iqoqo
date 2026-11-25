#!/usr/bin/env python3
"""Screen the catalog for cross-media FRBR Work relationships.

Heuristic blocking narrows the catalog to plausible cross-media Work pairs
(for example, a book Work and a film adaptation Work) without ever triggering
FRBR entity merges.  An optional local Ollama model (``--engine llama``) can
adjudicate surviving pairs.

The default mode is a dry run: add ``--apply`` to persist pending
``WorkLinkCandidate`` rows for custodian review.
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

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from app import create_app
from app.core import work_linking_service
from app.core.work_linking_service import (
    DEFAULT_ENGINE,
    DEFAULT_THRESHOLD,
    VALID_ENGINES,
    CrossMediaScanReport,
    WorkLinkingError,
    WorkLinkPrerequisiteError,
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_PREREQUISITE = 2

_SUMMARY_FIELDS: tuple[str, ...] = (
    "works_scanned",
    "candidate_pairs",
    "llm_evaluations",
    "llm_failures",
    "below_threshold",
    "already_known",
    "created",
    "would_create",
)


def _format_report(report: CrossMediaScanReport) -> str:
    """Render a scan report as a credential-free key=value summary."""
    return ", ".join(f"{name}={getattr(report, name)}" for name in _SUMMARY_FIELDS)


@dataclass(frozen=True)
class ScanOptions:
    """Configuration for a single cross-media reconciliation pass."""

    threshold: float = DEFAULT_THRESHOLD
    limit: int | None = None
    dry_run: bool = True
    skip_health_check: bool = False
    engine: str = DEFAULT_ENGINE


def run_scan(
    *,
    app: Any = None,
    options: ScanOptions | None = None,
    **kwargs: Any,
) -> CrossMediaScanReport:
    """Run one cross-media Work linking scan inside a Flask application context."""
    opts = options or ScanOptions(**kwargs)
    if opts.engine not in VALID_ENGINES:
        raise WorkLinkPrerequisiteError(f"Unknown engine: {opts.engine!r}. Expected one of {sorted(VALID_ENGINES)}")

    flask_app = app or create_app()
    with flask_app.app_context():
        return work_linking_service.scan_cross_media_links(
            engine=opts.engine,
            threshold=opts.threshold,
            limit=opts.limit,
            dry_run=opts.dry_run,
            skip_health_check=opts.skip_health_check,
        )


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum confidence required to queue a candidate, 0.0-1.0 (default: %(default)s)",
    )
    parser.add_argument(
        "--engine",
        choices=sorted(VALID_ENGINES),
        default=DEFAULT_ENGINE,
        help="heuristic resolves candidates deterministically; llama also adjudicates via Ollama (default: %(default)s)",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of Works to scan")
    parser.add_argument("--apply", action="store_true", help="Persist candidate rows; dry-run is the default")
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip the Ollama health probe (llama engine only)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress non-summary output")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute the cross-media Work linking CLI."""
    args = _build_parser().parse_args(argv)
    dry_run = not args.apply

    if not args.quiet:
        print(f"Engine: {args.engine}")
        print(f"Threshold: {args.threshold}")
        print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")

    try:
        report = run_scan(
            threshold=args.threshold,
            limit=args.limit,
            dry_run=dry_run,
            skip_health_check=args.skip_health_check,
            engine=args.engine,
        )
    except (WorkLinkPrerequisiteError, WorkLinkingError, ValueError) as exc:
        print(f"Reconciliation not started: {exc}", file=sys.stderr)
        return EXIT_PREREQUISITE
    except Exception as exc:  # Do not leak internal tracebacks or catalog secrets.
        print(f"Reconciliation aborted: {type(exc).__name__}", file=sys.stderr)
        return EXIT_FAILED

    print("Summary: " + _format_report(report))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
