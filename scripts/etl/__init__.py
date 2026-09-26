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
"""Safe FRBR ETL package for iqoqo.

Provides complete relationship coverage for FRBR duplicate reconciliation,
database backup verification, and merge plan execution.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified

from app import create_app
from app.db import db
from app.db.core import Expression, Item, Manifestation, Work
from scripts.etl.backup import create_complete_backup, verify_backup_coverage
from scripts.etl.merge import (
    MergeOperation,
    MergePlan,
    apply_manifestation_merge_plan,
    apply_work_merge_plan,
    generate_manifestation_merge_plan,
    generate_work_merge_plan,
)
from scripts.etl.reconcile import (
    ISBN_CLEAN_PATTERN,
    RelationshipInventory,
    ReparentPolicy,
    build_manifestation_relationship_inventory,
    build_work_relationship_inventory,
    isbn10_to_isbn13,
    normalize_isbn,
    normalize_to_isbn13,
)

__all__ = [
    "ISBN_CLEAN_PATTERN",
    "MergeOperation",
    "MergePlan",
    "RelationshipInventory",
    "ReparentPolicy",
    "apply_manifestation_merge_plan",
    "apply_work_merge_plan",
    "build_manifestation_relationship_inventory",
    "build_work_relationship_inventory",
    "create_complete_backup",
    "generate_manifestation_merge_plan",
    "generate_work_merge_plan",
    "isbn10_to_isbn13",
    "main",
    "normalize_isbn",
    "normalize_to_isbn13",
    "run_safe_etl_pipeline",
    "verify_backup_coverage",
]


def run_safe_etl_pipeline(
    dry_run: bool = False,
    backup_dir: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute the safe FRBR ETL pipeline with complete relationship coverage.

    :param dry_run: If True, generate merge plans without applying them
    :param backup_dir: Directory where backup is created
    :param verbose: If True, print detailed operational output
    :return: Statistics and merge plan summary
    """
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "backup_file": None,
        "backup_verification": None,
        "work_merge_plans": [],
        "manifestation_merge_plans": [],
        "conflicts": [],
        "stats": {
            "reconciled_works": 0,
            "reconciled_manifestations": 0,
            "reparented_expressions": 0,
            "reparented_items": 0,
            "reparented_scans": 0,
            "reparented_contributions": 0,
            "reparented_intents": 0,
            "reparented_feedback": 0,
            "reparented_notes": 0,
            "reparented_escalations": 0,
            "reparented_audit_logs": 0,
            "reparented_status_logs": 0,
            "merged_metadata": 0,
            "normalized_isbns": 0,
            "relocated_work_isbns": 0,
        },
    }

    # Step 0: Create and verify complete backup
    if not dry_run:
        b_dir = backup_dir or Path("exports/backups")
        try:
            backup_path = create_complete_backup(b_dir)
            result["backup_file"] = str(backup_path)

            # Verify backup coverage
            verification = verify_backup_coverage(backup_path)
            result["backup_verification"] = verification

            if not verification["valid"]:
                raise RuntimeError(f"Backup verification failed: {verification['error']}")

            if verbose:
                print(f"[BACKUP] Complete snapshot created at: {backup_path}")
                print(f"[BACKUP] Coverage verified: {verification['counts']}")
        except (RuntimeError, OSError, json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError(f"Backup creation/verification failed: {exc}") from exc

    # Step 1: Normalize ISBNs and relocate Work-level ISBNs
    works = db.session.execute(select(Work)).scalars().all()
    for work in works:
        if not work.meta or not isinstance(work.meta, dict):
            continue

        work_meta = dict(work.meta)
        misplaced_isbn = None
        for key in ("isbn", "isbn13", "ISBN", "ISBN13"):
            if key in work_meta and work_meta[key]:
                misplaced_isbn = str(work_meta[key]).strip()
                del work_meta[key]

        if misplaced_isbn:
            normalized = normalize_to_isbn13(misplaced_isbn)
            work.meta = work_meta
            flag_modified(work, "meta")
            result["stats"]["relocated_work_isbns"] += 1

            if normalized:
                existing_manif = db.session.execute(select(Manifestation).where(Manifestation.isbn13 == normalized)).scalars().first()
                if not existing_manif:
                    child_exprs = db.session.execute(select(Expression).where(Expression.work_id == work.id)).scalars().all()
                    assigned = False
                    for expr in child_exprs:
                        if assigned:
                            break
                        child_manifs = (
                            db.session.execute(select(Manifestation).where(Manifestation.expression_id == expr.id)).scalars().all()
                        )
                        for manif in child_manifs:
                            if not manif.isbn13:
                                manif.isbn13 = normalized
                                assigned = True
                                result["stats"]["normalized_isbns"] += 1
                                if verbose:
                                    print(f"[NORMALIZE] Assigned ISBN {normalized} to Manifestation {manif.id}")
                                break

    if not dry_run:
        db.session.flush()

    # Step 2: Deduplicate Manifestations
    all_manifs = db.session.execute(select(Manifestation)).scalars().all()
    isbn_groups: dict[str, list[tuple[Manifestation, str]]] = defaultdict(list)
    for m in all_manifs:
        if m.isbn13:
            norm_isbn = normalize_to_isbn13(m.isbn13) or ISBN_CLEAN_PATTERN.sub("", m.isbn13.upper())
            if norm_isbn:
                isbn_groups[norm_isbn].append((m, norm_isbn))

    for _isbn_key, group in isbn_groups.items():
        if len(group) == 1:
            m, target_isbn = group[0]
            if m.isbn13 != target_isbn:
                m.isbn13 = target_isbn
                result["stats"]["normalized_isbns"] += 1
                if verbose:
                    print(f"[NORMALIZE] Manifestation {m.id}: '{m.isbn13}' -> '{target_isbn}'")
            continue

        # Canonical manifestation: select record with highest item count or oldest id
        group_with_counts = []
        for m, target_isbn in group:
            item_count = len(db.session.execute(select(Item).where(Item.manifestation_id == m.id)).scalars().all())
            group_with_counts.append((item_count, -m.id, m, target_isbn))
        group_with_counts.sort(reverse=True)

        canonical = group_with_counts[0][2]
        canonical_target = group_with_counts[0][3]
        duplicates = [item[2] for item in group_with_counts[1:]]

        if canonical.isbn13 != canonical_target:
            canonical.isbn13 = canonical_target
            result["stats"]["normalized_isbns"] += 1

        for dup in duplicates:
            # Generate merge plan
            plan = generate_manifestation_merge_plan(canonical, dup)
            result["manifestation_merge_plans"].append(
                {
                    "canonical_id": plan.canonical_id,
                    "duplicate_id": plan.duplicate_id,
                    "operations": len(plan.operations),
                    "conflicts": plan.conflicts,
                }
            )
            result["conflicts"].extend(plan.conflicts)

            if plan.has_conflicts():
                if verbose:
                    print(f"[CONFLICT] Manifestation merge {dup.id} -> {canonical.id}: {plan.conflicts}")
                continue

            if dry_run:
                if verbose:
                    print(f"[DRY RUN] Would merge Manifestation {dup.id} into {canonical.id}")
            else:
                # Apply merge plan
                try:
                    stats = apply_manifestation_merge_plan(plan, dry_run=False)
                    for key, value in stats.items():
                        result["stats"][key] = result["stats"].get(key, 0) + value
                    result["stats"]["reconciled_manifestations"] += 1
                    if verbose:
                        print(f"[MERGE] Manifestation {dup.id} merged into {canonical.id}")
                except (RuntimeError, ValueError, KeyError, SQLAlchemyError) as exc:
                    db.session.rollback()
                    raise RuntimeError(f"Manifestation merge failed: {exc}") from exc

    if not dry_run:
        db.session.flush()

    # Step 3: Deduplicate Works
    all_works = db.session.execute(select(Work)).scalars().all()
    work_groups: dict[str, list[Work]] = defaultdict(list)
    for w in all_works:
        authors: list[str] = []
        if w.meta and isinstance(w.meta, dict):
            raw_authors = w.meta.get("authors") or w.meta.get("Authors") or []
            if isinstance(raw_authors, list):
                authors = sorted(str(a).strip().lower() for a in raw_authors if str(a).strip())
        norm_title = (w.title or "").strip().lower()
        key = f"{norm_title}||{'|'.join(authors)}"
        work_groups[key].append(w)

    for cluster_key, w_group in work_groups.items():
        if len(w_group) <= 1 or not cluster_key.strip("|"):
            continue

        # Canonical work: select oldest id
        w_group.sort(key=lambda item: item.id)
        canonical_work = w_group[0]
        duplicate_works = w_group[1:]

        for dup_work in duplicate_works:
            # Generate merge plan
            plan = generate_work_merge_plan(canonical_work, dup_work)
            result["work_merge_plans"].append(
                {
                    "canonical_id": plan.canonical_id,
                    "duplicate_id": plan.duplicate_id,
                    "operations": len(plan.operations),
                    "conflicts": plan.conflicts,
                }
            )
            result["conflicts"].extend(plan.conflicts)

            if plan.has_conflicts():
                if verbose:
                    print(f"[CONFLICT] Work merge {dup_work.id} -> {canonical_work.id}: {plan.conflicts}")
                continue

            if dry_run:
                if verbose:
                    print(f"[DRY RUN] Would merge Work {dup_work.id} into {canonical_work.id}")
            else:
                # Apply merge plan
                try:
                    stats = apply_work_merge_plan(plan, dry_run=False)
                    for key, value in stats.items():
                        result["stats"][key] = result["stats"].get(key, 0) + value
                    result["stats"]["reconciled_works"] += 1
                    if verbose:
                        print(f"[MERGE] Work {dup_work.id} merged into {canonical_work.id}")
                except (RuntimeError, ValueError, KeyError, SQLAlchemyError) as exc:
                    db.session.rollback()
                    raise RuntimeError(f"Work merge failed: {exc}") from exc

    if dry_run:
        db.session.rollback()
        if verbose:
            print("\n[DRY RUN] Simulation complete. No database modifications were committed.")
    else:
        db.session.commit()
        if verbose:
            print("\n[LIVE] ETL transaction committed successfully.")

    return result


def main() -> None:
    """CLI entrypoint for safe FRBR ETL operations."""
    parser = argparse.ArgumentParser(description="Safe FRBR Database ETL with Complete Relationship Coverage.")
    parser.add_argument("--dry-run", action="store_true", help="Generate merge plans without applying them.")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("exports/backups"),
        help="Directory for backup snapshots.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed operation steps.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        result = run_safe_etl_pipeline(
            dry_run=args.dry_run,
            backup_dir=args.backup_dir,
            verbose=args.verbose,
        )

    print("=" * 64)
    print("SAFE FRBR ETL EXECUTION SUMMARY" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 64)
    print(f"Reconciled Works:                  {result['stats']['reconciled_works']}")
    print(f"Reconciled Manifestations:         {result['stats']['reconciled_manifestations']}")
    print(f"Reparented Expressions:            {result['stats']['reparented_expressions']}")
    print(f"Reparented Items:                  {result['stats']['reparented_items']}")
    print(f"Reparented Image Scans:            {result['stats']['reparented_scans']}")
    print(f"Reparented Contributions:          {result['stats']['reparented_contributions']}")
    print(f"Reparented User Intents:           {result['stats']['reparented_intents']}")
    print(f"Reparented Social Feedback:        {result['stats']['reparented_feedback']}")
    print(f"Reparented Social Notes:           {result['stats']['reparented_notes']}")
    print(f"Reparented Escalation Requests:    {result['stats']['reparented_escalations']}")
    print(f"Reparented Audit Logs:             {result['stats']['reparented_audit_logs']}")
    print(f"Reparented Status Logs:            {result['stats']['reparented_status_logs']}")
    print(f"Merged Metadata:                   {result['stats']['merged_metadata']}")
    print(f"Normalized ISBNs:                  {result['stats']['normalized_isbns']}")
    print(f"Relocated Work ISBNs:              {result['stats']['relocated_work_isbns']}")
    print(f"Conflicts Detected:                {len(result['conflicts'])}")
    if result["backup_file"]:
        print(f"Backup File:                       {result['backup_file']}")
    print("=" * 64)

    if result["conflicts"]:
        print("\nConflicts:")
        for conflict in result["conflicts"]:
            print(f"  - {conflict}")


if __name__ == "__main__":
    main()
