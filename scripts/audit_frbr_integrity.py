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
"""FRBR Integrity Audit Script.

Audits FRBR Group 1 relationships and reports:
- Orphaned Expressions (missing Work), Manifestations (missing Expression), Items (missing Manifestation)
- Duplicate Works (same title and authors) and duplicate Manifestations (identical normalized ISBN)
- ISBN violations (checksum errors, invalid length, Work-level placement)

Usage:
    python scripts/audit_frbr_integrity.py [--json] [--verbose] [--output PATH]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402
from app.db.core import Expression, Item, Manifestation, Work  # noqa: E402

ISBN13_CLEAN_PATTERN = re.compile(r"[^0-9X]")


def validate_isbn10_checksum(isbn: str) -> bool:
    """Validate 10-digit ISBN checksum using modulo 11 algorithm.

    :param isbn: Raw or cleaned ISBN-10 string
    :return: True if check digit is mathematically valid, False otherwise
    """
    cleaned = ISBN13_CLEAN_PATTERN.sub("", isbn.upper())
    if len(cleaned) != 10:
        return False
    if not (cleaned[:9].isdigit() and (cleaned[9].isdigit() or cleaned[9] == "X")):
        return False
    total = sum((10 - idx) * (10 if char == "X" else int(char)) for idx, char in enumerate(cleaned))
    return total % 11 == 0


def validate_isbn13_checksum(isbn: str) -> bool:
    """Validate 13-digit ISBN checksum using modulo 10 (EAN-13) algorithm.

    :param isbn: Raw or cleaned ISBN-13 string
    :return: True if check digit is mathematically valid, False otherwise
    """
    cleaned = ISBN13_CLEAN_PATTERN.sub("", isbn.upper())
    if len(cleaned) != 13 or not cleaned.isdigit():
        return False
    total = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(cleaned[:12]))
    expected_check = (10 - (total % 10)) % 10
    return int(cleaned[12]) == expected_check


def audit_orphan_entities() -> dict[str, list[dict[str, Any]]]:
    """Identify orphaned Expressions, Manifestations, and Items lacking parent records.

    :return: Dictionary partitioned by entity category listing orphan details
    """
    orphan_expressions: list[dict[str, Any]] = []
    orphan_manifestations: list[dict[str, Any]] = []
    orphan_items: list[dict[str, Any]] = []

    # Expressions without Work
    expr_stmt = select(Expression).where(
        Expression.work_id.is_(None) | ~Expression.work_id.in_(select(Work.id))
    )
    for expr in db.session.execute(expr_stmt).scalars().all():
        orphan_expressions.append({
            "id": expr.id,
            "work_id": expr.work_id,
            "content_type": expr.content_type,
            "language": expr.language,
        })

    # Manifestations without Expression
    manif_stmt = select(Manifestation).where(
        Manifestation.expression_id.is_(None)
        | ~Manifestation.expression_id.in_(select(Expression.id))
    )
    for manif in db.session.execute(manif_stmt).scalars().all():
        orphan_manifestations.append({
            "id": manif.id,
            "expression_id": manif.expression_id,
            "isbn13": manif.isbn13,
            "publisher": manif.publisher,
        })

    # Items without Manifestation
    item_stmt = select(Item).where(
        Item.manifestation_id.is_(None)
        | ~Item.manifestation_id.in_(select(Manifestation.id))
    )
    for item in db.session.execute(item_stmt).scalars().all():
        orphan_items.append({
            "id": item.id,
            "manifestation_id": item.manifestation_id,
            "status": getattr(item, "status", None),
        })

    return {
        "expressions": orphan_expressions,
        "manifestations": orphan_manifestations,
        "items": orphan_items,
    }


def audit_duplicate_entities() -> dict[str, list[dict[str, Any]]]:
    """Detect duplicate Works sharing titles/authors and Manifestations sharing ISBNs.

    :return: Dictionary containing candidate duplicate clusters
    """
    # Duplicate Works
    works_stmt = select(Work)
    works = db.session.execute(works_stmt).scalars().all()
    work_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for work in works:
        authors: list[str] = []
        if work.meta and isinstance(work.meta, dict):
            raw_authors = work.meta.get("authors") or work.meta.get("Authors") or []
            if isinstance(raw_authors, list):
                authors = sorted(str(author).strip().lower() for author in raw_authors if str(author).strip())
        norm_title = (work.title or "").strip().lower()
        key = f"{norm_title}||{'|'.join(authors)}"
        work_groups[key].append({
            "id": work.id,
            "title": work.title,
            "authors": authors,
        })

    duplicate_works = [
        {"cluster_key": key, "count": len(items), "entities": items}
        for key, items in work_groups.items()
        if len(items) > 1 and key.strip("|")
    ]

    # Duplicate Manifestations by normalized ISBN-13
    manif_stmt = select(Manifestation).where(Manifestation.isbn13.isnot(None))
    manifs = db.session.execute(manif_stmt).scalars().all()
    manif_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for manif in manifs:
        if not manif.isbn13:
            continue
        cleaned_isbn = ISBN13_CLEAN_PATTERN.sub("", manif.isbn13.upper())
        if cleaned_isbn:
            manif_groups[cleaned_isbn].append({
                "id": manif.id,
                "raw_isbn13": manif.isbn13,
                "publisher": manif.publisher,
            })

    duplicate_manifestations = [
        {"isbn13": key, "count": len(items), "entities": items}
        for key, items in manif_groups.items()
        if len(items) > 1
    ]

    return {
        "works": duplicate_works,
        "manifestations": duplicate_manifestations,
    }


def audit_isbn_violations() -> list[dict[str, Any]]:
    """Scan catalog entities for invalid ISBN formats, checksum failures, and improper placement.

    :return: List of ISBN violation records
    """
    violations: list[dict[str, Any]] = []

    # 1. Inspect Manifestation ISBNs
    manif_stmt = select(Manifestation).where(Manifestation.isbn13.isnot(None))
    manifestations = db.session.execute(manif_stmt).scalars().all()

    for manif in manifestations:
        raw_isbn = manif.isbn13
        if not raw_isbn:
            continue
        cleaned = ISBN13_CLEAN_PATTERN.sub("", raw_isbn.upper())

        if len(cleaned) == 10:
            if validate_isbn10_checksum(cleaned):
                violations.append({
                    "entity_type": "Manifestation",
                    "entity_id": manif.id,
                    "violation": "isbn10_unnormalized",
                    "value": raw_isbn,
                    "detail": "Valid 10-digit ISBN stored in isbn13 column without conversion",
                })
            else:
                violations.append({
                    "entity_type": "Manifestation",
                    "entity_id": manif.id,
                    "violation": "invalid_checksum_isbn10",
                    "value": raw_isbn,
                    "detail": "10-digit ISBN with invalid modulo 11 check digit",
                })
        elif len(cleaned) == 13:
            if not validate_isbn13_checksum(cleaned):
                violations.append({
                    "entity_type": "Manifestation",
                    "entity_id": manif.id,
                    "violation": "invalid_checksum_isbn13",
                    "value": raw_isbn,
                    "detail": "13-digit ISBN with invalid EAN-13 check digit",
                })
        else:
            violations.append({
                "entity_type": "Manifestation",
                "entity_id": manif.id,
                "violation": "invalid_length",
                "value": raw_isbn,
                "detail": f"ISBN length {len(cleaned)} is neither 10 nor 13 digits",
            })

    # 2. Inspect Work entities for misplaced ISBN attributes
    work_stmt = select(Work)
    works = db.session.execute(work_stmt).scalars().all()

    for work in works:
        if not work.meta or not isinstance(work.meta, dict):
            continue
        for key in ("isbn", "isbn13", "ISBN", "ISBN13"):
            if key in work.meta and work.meta[key]:
                violations.append({
                    "entity_type": "Work",
                    "entity_id": work.id,
                    "violation": "work_level_isbn",
                    "value": str(work.meta[key]),
                    "detail": f"ISBN attribute '{key}' misplaced on Work entity instead of Manifestation",
                })

    return violations


def run_audit() -> dict[str, Any]:
    """Execute complete FRBR database integrity check and compute metrics.

    :return: Dictionary containing audit report data and summary counts
    """
    orphans = audit_orphan_entities()
    duplicates = audit_duplicate_entities()
    isbn_violations = audit_isbn_violations()

    summary = {
        "orphan_expressions_count": len(orphans["expressions"]),
        "orphan_manifestations_count": len(orphans["manifestations"]),
        "orphan_items_count": len(orphans["items"]),
        "duplicate_work_clusters": len(duplicates["works"]),
        "duplicate_manifestation_clusters": len(duplicates["manifestations"]),
        "isbn_violations_count": len(isbn_violations),
    }

    summary["total_violations"] = (
        summary["orphan_expressions_count"]
        + summary["orphan_manifestations_count"]
        + summary["orphan_items_count"]
        + summary["duplicate_work_clusters"]
        + summary["duplicate_manifestation_clusters"]
        + summary["isbn_violations_count"]
    )

    return {
        "orphans": orphans,
        "duplicates": duplicates,
        "isbn_violations": isbn_violations,
        "summary": summary,
    }


def main() -> None:
    """CLI entrypoint for FRBR integrity audit."""
    parser = argparse.ArgumentParser(description="FRBR Database Integrity Audit Tool.")
    parser.add_argument("--json", action="store_true", help="Output audit results as JSON to stdout.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed entity listings.")
    parser.add_argument("--output", type=Path, default=None, help="Save JSON audit report to specified file path.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        report = run_audit()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["summary"]["total_violations"] == 0 else 1)

    # Human-readable CLI formatting
    summary = report["summary"]
    print("=" * 64)
    print("FRBR DATABASE INTEGRITY AUDIT REPORT")
    print("=" * 64)
    print(f"Orphan Expressions (no Work):           {summary['orphan_expressions_count']}")
    print(f"Orphan Manifestations (no Expression):  {summary['orphan_manifestations_count']}")
    print(f"Orphan Items (no Manifestation):        {summary['orphan_items_count']}")
    print(f"Duplicate Work clusters:                {summary['duplicate_work_clusters']}")
    print(f"Duplicate Manifestation clusters:       {summary['duplicate_manifestation_clusters']}")
    print(f"ISBN format/placement violations:       {summary['isbn_violations_count']}")
    print("-" * 64)
    print(f"Total integrity violations:             {summary['total_violations']}")
    print("=" * 64)

    if args.verbose and summary["total_violations"] > 0:
        if summary["orphan_expressions_count"]:
            print("\n--- Orphan Expressions ---")
            for item in report["orphans"]["expressions"][:10]:
                print(f"  [Expression {item['id']}] work_id={item['work_id']} type={item['content_type']}")

        if summary["orphan_manifestations_count"]:
            print("\n--- Orphan Manifestations ---")
            for item in report["orphans"]["manifestations"][:10]:
                print(f"  [Manifestation {item['id']}] expr_id={item['expression_id']} isbn={item['isbn13']}")

        if summary["orphan_items_count"]:
            print("\n--- Orphan Items ---")
            for item in report["orphans"]["items"][:10]:
                print(f"  [Item {item['id']}] manif_id={item['manifestation_id']} status={item['status']}")

        if summary["duplicate_work_clusters"]:
            print("\n--- Duplicate Works ---")
            for cluster in report["duplicates"]["works"][:5]:
                print(f"  Cluster '{cluster['cluster_key']}' ({cluster['count']} entities)")

        if summary["duplicate_manifestation_clusters"]:
            print("\n--- Duplicate Manifestations ---")
            for cluster in report["duplicates"]["manifestations"][:5]:
                print(f"  ISBN {cluster['isbn13']} ({cluster['count']} entities)")

        if summary["isbn_violations_count"]:
            print("\n--- ISBN Violations ---")
            for viol in report["isbn_violations"][:10]:
                print(f"  [{viol['entity_type']} {viol['entity_id']}] {viol['violation']}: {viol['value']} ({viol['detail']})")

    sys.exit(0 if summary["total_violations"] == 0 else 1)


if __name__ == "__main__":
    main()
