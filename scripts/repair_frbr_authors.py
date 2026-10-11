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
"""CLI utility to repair FRBR work author metadata and contributor relationships.

Validates and normalizes work.meta["authors"] entries, reconciles WorkContribution
entities, and ensures author list consistency across the catalog.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app import create_app
from app.core.frbr_service import normalize_authors_list, sync_entity_contributions
from app.db.contributions import WorkContribution
from app.db.models import Work, db


def repair_work_authors(apply_changes: bool = False, batch_size: int = 500) -> tuple[int, int]:
    """Inspect and optionally repair work author metadata and contributions.

    Parameters
    ----------
    apply_changes:
        If True, writes updates to the database. If False, runs in dry-run mode.
    batch_size:
        Number of Work records to process per batch for constant memory usage.

    Returns
    -------
    tuple[int, int]
        (inspected_count, repaired_count)
    """
    total_count_stmt = select(func.count()).select_from(Work)  # pylint: disable=not-callable
    inspected = db.session.execute(total_count_stmt).scalar() or 0
    repaired = 0

    print(f"Scanning {inspected} works (Mode: {'APPLY' if apply_changes else 'DRY RUN'})...")

    offset = 0
    while True:
        stmt = (
            select(Work)
            .options(selectinload(Work.contributions).selectinload(WorkContribution.contributor))
            .order_by(Work.id)
            .offset(offset)
            .limit(batch_size)
        )
        batch: Sequence[Work] = db.session.execute(stmt).scalars().all()
        if not batch:
            break

        batch_repaired = 0
        for work in batch:
            meta = dict(work.meta or {})
            raw_authors = meta.get("authors")
            normalized = normalize_authors_list(raw_authors)

            needs_repair = False

            # Condition 1: raw_authors is not already a list of clean strings equal to normalized
            if raw_authors != normalized:
                needs_repair = True

            # Condition 2: check if WorkContribution rows exist and match normalized
            existing_contributions = work.contributions
            existing_names = {c.contributor.name for c in existing_contributions if c.contributor} if existing_contributions else set()
            expected_names = set(normalized)

            if normalized and existing_names != expected_names:
                needs_repair = True

            if needs_repair:
                repaired += 1
                batch_repaired += 1
                print(f"Work id={work.id} ('{work.title}'):\n" f"  Raw: {raw_authors!r}\n" f"  Normalized: {normalized!r}")

                if apply_changes:
                    meta["authors"] = normalized
                    work.meta = meta
                    flag_modified(work, "meta")

                    if normalized:
                        contributions_payload = [{"name": name, "role": "author"} for name in normalized]
                        sync_entity_contributions(work, contributions_payload)

        if apply_changes and batch_repaired > 0:
            db.session.commit()

        offset += len(batch)
        if len(batch) < batch_size:
            break

    if apply_changes:
        print(f"Repair complete: {repaired} works updated and committed.")
    else:
        print(f"Dry run complete: {repaired} works need repair. Run with --apply to execute changes.")

    return inspected, repaired


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair FRBR work author metadata and contributions.")
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to the database. Without this flag, script runs in dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Explicitly run in dry-run mode (default behavior).",
    )
    args = parser.parse_args()

    apply_mode = args.apply and not args.dry_run

    app = create_app()
    with app.app_context():
        repair_work_authors(apply_changes=apply_mode)


if __name__ == "__main__":
    main()
