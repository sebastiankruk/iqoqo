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
"""Strict FRBR ETL Reconciliation and Normalization Script.

Operations:
- Pre-execution verified database point-in-time backup
- Normalization of ISBN-10 to standard 13-digit EAN-13 format
- Relocation of misplaced Work-level ISBN identifiers to child Manifestations
- Deduplication of Manifestations with physical Item reparenting
- Deduplication of Works with Expression reparenting
- Idempotent execution with --dry-run support

Usage:
    python scripts/etl_frbr_strict.py [--dry-run] [--skip-backup] [--backup-dir DIR] [--verbose]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402
from app.db.core import Expression, Item, Manifestation, Work  # noqa: E402

ISBN_CLEAN_PATTERN = re.compile(r"[^0-9X]")


def isbn10_to_isbn13(isbn10: str) -> str | None:
    """Convert a valid 10-digit ISBN into a standard 13-digit EAN-13 ISBN.

    :param isbn10: Raw or formatted 10-digit ISBN string
    :return: Normalized 13-digit ISBN string or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", isbn10.upper())
    if len(cleaned) != 10:
        return None

    # Validate 10-digit checksum
    if not (cleaned[:9].isdigit() and (cleaned[9].isdigit() or cleaned[9] == "X")):
        return None
    total10 = sum((10 - idx) * (10 if char == "X" else int(char)) for idx, char in enumerate(cleaned))
    if total10 % 11 != 0:
        return None

    # Construct 13-digit prefix (978 + first 9 digits)
    core = f"978{cleaned[:9]}"
    total13 = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(core))
    check13 = (10 - (total13 % 10)) % 10
    return f"{core}{check13}"


def normalize_to_isbn13(raw_isbn: str) -> str | None:
    """Normalize any ISBN (10-digit or 13-digit) to a canonical 13-digit string.

    :param raw_isbn: Raw ISBN string containing possible hyphens or spaces
    :return: Normalized 13-digit ISBN or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", raw_isbn.upper())
    if len(cleaned) == 10:
        return isbn10_to_isbn13(cleaned)
    if len(cleaned) == 13 and cleaned.isdigit():
        total = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(cleaned[:12]))
        expected_check = (10 - (total % 10)) % 10
        if int(cleaned[12]) == expected_check:
            return cleaned
    return None


# Alias for cleaner API
normalize_isbn = normalize_to_isbn13


def create_pre_execution_backup(backup_dir: Path) -> Path:
    """Create a verified point-in-time JSON snapshot of core FRBR entities before data mutation.

    :param backup_dir: Destination directory for the backup archive
    :return: Path to the generated and verified backup file
    :raises RuntimeError: If backup generation or verification fails
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"frbr_snapshot_{timestamp}.json"

    works = db.session.execute(select(Work)).scalars().all()
    expressions = db.session.execute(select(Expression)).scalars().all()
    manifestations = db.session.execute(select(Manifestation)).scalars().all()
    items = db.session.execute(select(Item)).scalars().all()

    snapshot_data: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "counts": {
            "works": len(works),
            "expressions": len(expressions),
            "manifestations": len(manifestations),
            "items": len(items),
        },
        "entities": {
            "works": [{"id": w.id, "title": w.title, "meta": w.meta} for w in works],
            "expressions": [
                {"id": e.id, "work_id": e.work_id, "content_type": e.content_type, "language": e.language, "kind": e.kind}
                for e in expressions
            ],
            "manifestations": [
                {
                    "id": m.id,
                    "expression_id": m.expression_id,
                    "isbn13": m.isbn13,
                    "publisher": m.publisher,
                    "meta": m.meta,
                }
                for m in manifestations
            ],
            "items": [
                {
                    "id": i.id,
                    "manifestation_id": i.manifestation_id,
                    "owner_id": str(i.owner_id) if i.owner_id is not None else None,
                    "status": getattr(i, "status", None),
                }
                for i in items
            ],
        },
    }

    try:
        backup_file.write_text(json.dumps(snapshot_data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to write backup snapshot to {backup_file}: {exc}") from exc

    # Verify backup exists and is readable
    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise RuntimeError(f"Backup verification failed: file {backup_file} is missing or empty")

    return backup_file


def run_etl_pipeline(
    dry_run: bool = False,
    skip_backup: bool = False,
    backup_dir: Path | None = None,
    verbose: bool = False,
) -> dict[str, int]:
    """Execute the full FRBR data reconciliation and normalization pipeline.

    :param dry_run: If True, compute changes without committing to database
    :param skip_backup: If True, bypass the pre-execution backup step
    :param backup_dir: Directory where pre-execution backup is created
    :param verbose: If True, print detailed operational output
    :return: Statistics dictionary summarizing performed fixes
    """
    stats = {
        "reconciled_works": 0,
        "reconciled_manifestations": 0,
        "reparented_items": 0,
        "reparented_expressions": 0,
        "normalized_isbns": 0,
        "relocated_work_isbns": 0,
    }

    # Step 0: Pre-execution backup
    if not dry_run and not skip_backup:
        b_dir = backup_dir or Path("exports/backups")
        backup_path = create_pre_execution_backup(b_dir)
        if verbose:
            print(f"[BACKUP] Verified point-in-time snapshot created at: {backup_path}")

    # Step 1: Relocate misplaced Work-level ISBNs to child Manifestations
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
            stats["relocated_work_isbns"] += 1

            if normalized:
                existing_manif = db.session.execute(select(Manifestation).where(Manifestation.isbn13 == normalized)).scalars().first()
                if not existing_manif:
                    # Find child manifestations under this Work to receive the ISBN if missing
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
                                if verbose:
                                    print(f"[RELOCATE] Assigned ISBN {normalized} to Manifestation {manif.id} from Work {work.id}")
                                break

    if not dry_run:
        db.session.flush()

    # Step 2 & 3: Normalize and deduplicate Manifestations sharing identical normalized ISBN-13
    all_manifs = db.session.execute(select(Manifestation)).scalars().all()
    isbn_groups: dict[str, list[tuple[Manifestation, str]]] = defaultdict(list)
    for m in all_manifs:
        if m.isbn13:
            norm_isbn = normalize_to_isbn13(m.isbn13) or ISBN_CLEAN_PATTERN.sub("", m.isbn13.upper())
            if norm_isbn:
                isbn_groups[norm_isbn].append((m, norm_isbn))

    for isbn_key, group in isbn_groups.items():
        if len(group) == 1:
            m, target_isbn = group[0]
            if m.isbn13 != target_isbn:
                if verbose:
                    print(f"[NORMALIZE] Manifestation {m.id}: '{m.isbn13}' -> '{target_isbn}'")
                m.isbn13 = target_isbn
                stats["normalized_isbns"] += 1
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
            if verbose:
                print(f"[NORMALIZE] Manifestation {canonical.id}: '{canonical.isbn13}' -> '{canonical_target}'")
            canonical.isbn13 = canonical_target
            stats["normalized_isbns"] += 1

        for dup in duplicates:
            # Reparent all items from duplicate to canonical
            dup_items = db.session.execute(select(Item).where(Item.manifestation_id == dup.id)).scalars().all()
            for itm in dup_items:
                itm.manifestation_id = canonical.id
                stats["reparented_items"] += 1

            # Merge metadata
            if dup.meta and isinstance(dup.meta, dict):
                canon_meta = dict(canonical.meta or {})
                for k, v in dup.meta.items():
                    if k not in canon_meta:
                        canon_meta[k] = v
                canonical.meta = canon_meta
                flag_modified(canonical, "meta")

            db.session.delete(dup)
            stats["reconciled_manifestations"] += 1
            if verbose:
                print(f"[MERGE MANIF] Duplicate Manifestation {dup.id} merged into canonical {canonical.id} (ISBN {isbn_key})")

    if not dry_run:
        db.session.flush()

    # Step 4: Deduplicate Works sharing identical normalized title and authors
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
            # Reparent all expressions from duplicate to canonical work
            dup_exprs = db.session.execute(select(Expression).where(Expression.work_id == dup_work.id)).scalars().all()
            for expr in dup_exprs:
                expr.work_id = canonical_work.id
                stats["reparented_expressions"] += 1

            # Merge metadata
            if dup_work.meta and isinstance(dup_work.meta, dict):
                canon_meta = dict(canonical_work.meta or {})
                for k, v in dup_work.meta.items():
                    if k not in canon_meta:
                        canon_meta[k] = v
                canonical_work.meta = canon_meta
                flag_modified(canonical_work, "meta")

            db.session.delete(dup_work)
            stats["reconciled_works"] += 1
            if verbose:
                print(f"[MERGE WORK] Duplicate Work {dup_work.id} merged into canonical {canonical_work.id} ('{canonical_work.title}')")

    if dry_run:
        db.session.rollback()
        if verbose:
            print("\n[DRY RUN] Simulation complete. No database modifications were committed.")
    else:
        db.session.commit()
        if verbose:
            print("\n[LIVE] ETL transaction committed successfully.")

    return stats


def main() -> None:
    """CLI entrypoint for strict FRBR ETL operations."""
    parser = argparse.ArgumentParser(description="Strict FRBR Database ETL and Reconciliation Tool.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate ETL changes without modifying database.")
    parser.add_argument("--skip-backup", action="store_true", help="Bypass pre-execution point-in-time backup.")
    parser.add_argument("--backup-dir", type=Path, default=Path("exports/backups"), help="Directory for backup snapshots.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed operation steps.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stats = run_etl_pipeline(
            dry_run=args.dry_run,
            skip_backup=args.skip_backup,
            backup_dir=args.backup_dir,
            verbose=args.verbose,
        )

    print("=" * 64)
    print("STRICT FRBR ETL EXECUTION SUMMARY" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 64)
    print(f"Reconciled Duplicate Works:          {stats['reconciled_works']}")
    print(f"Reparented Expressions:              {stats['reparented_expressions']}")
    print(f"Reconciled Duplicate Manifestations: {stats['reconciled_manifestations']}")
    print(f"Reparented Physical Items:           {stats['reparented_items']}")
    print(f"Normalized ISBN Identifiers:         {stats['normalized_isbns']}")
    print(f"Relocated Work-level ISBNs:          {stats['relocated_work_isbns']}")
    print("=" * 64)


if __name__ == "__main__":
    main()
