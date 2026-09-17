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
"""
FRBR Integrity Audit Script.

Detects:
- Orphan Manifestations without Expression
- Expressions without Work
- Duplicate Works (same title + authors)
- ISBN-13 format violations

Usage:
    python scripts/audit_frbr_integrity.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.db.models import Expression, Manifestation, Work

ISBN13_PATTERN = re.compile(r"^\d{13}$")


def audit_orphan_manifestations() -> list[dict]:
    """Find Manifestations that have no linked Expression."""
    orphans = []
    manifestations = Manifestation.query.filter(Manifestation.expression_id.is_(None)).all()
    for m in manifestations:
        orphans.append({"id": str(m.id), "title": getattr(m, "title", None), "isbn13": m.isbn13})
    return orphans


def audit_orphan_expressions() -> list[dict]:
    """Find Expressions that have no linked Work."""
    orphans = []
    expressions = Expression.query.filter(Expression.work_id.is_(None)).all()
    for e in expressions:
        orphans.append({"id": str(e.id), "content_type": e.content_type, "language": e.language})
    return orphans


def audit_duplicate_works() -> list[dict]:
    """Find Works with the same title and authors (potential duplicates)."""
    works = Work.query.all()
    groups: dict[str, list] = defaultdict(list)

    for w in works:
        authors = sorted((w.meta or {}).get("authors", []) or (w.meta or {}).get("Authors", []))
        key = f"{(w.title or '').strip().lower()}|{'|'.join(a.lower() for a in authors)}"
        groups[key].append({"id": str(w.id), "title": w.title, "authors": authors})

    duplicates = []
    for key, items in groups.items():
        if len(items) > 1:
            duplicates.append({"key": key, "count": len(items), "works": items})
    return duplicates


def audit_isbn_violations() -> list[dict]:
    """Find Manifestations with invalid ISBN-13 format."""
    violations = []
    manifestations = Manifestation.query.filter(Manifestation.isbn13.isnot(None)).all()
    for m in manifestations:
        if m.isbn13 and not ISBN13_PATTERN.match(m.isbn13):
            violations.append({"id": str(m.id), "isbn13": m.isbn13, "title": getattr(m, "title", None)})
    return violations


def run_audit() -> dict:
    """Run all audits and return a report."""
    report = {
        "orphan_manifestations": audit_orphan_manifestations(),
        "orphan_expressions": audit_orphan_expressions(),
        "duplicate_works": audit_duplicate_works(),
        "isbn_violations": audit_isbn_violations(),
    }

    report["summary"] = {
        "orphan_manifestations_count": len(report["orphan_manifestations"]),
        "orphan_expressions_count": len(report["orphan_expressions"]),
        "duplicate_work_groups": len(report["duplicate_works"]),
        "isbn_violations_count": len(report["isbn_violations"]),
    }
    return report


def main():
    app = create_app()
    with app.app_context():
        report = run_audit()

        print("=" * 60)
        print("FRBR INTEGRITY AUDIT REPORT")
        print("=" * 60)
        print()

        summary = report["summary"]
        print(f"Orphan Manifestations (no Expression): {summary['orphan_manifestations_count']}")
        print(f"Orphan Expressions (no Work):          {summary['orphan_expressions_count']}")
        print(f"Duplicate Work groups:                 {summary['duplicate_work_groups']}")
        print(f"ISBN-13 format violations:             {summary['isbn_violations_count']}")
        print()

        if summary["orphan_manifestations_count"]:
            print("--- Orphan Manifestations ---")
            for item in report["orphan_manifestations"][:10]:
                print(f"  ID={item['id']}  ISBN={item['isbn13']}  Title={item['title']}")
            if summary["orphan_manifestations_count"] > 10:
                print(f"  ... and {summary['orphan_manifestations_count'] - 10} more")
            print()

        if summary["orphan_expressions_count"]:
            print("--- Orphan Expressions ---")
            for item in report["orphan_expressions"][:10]:
                print(f"  ID={item['id']}  type={item['content_type']}  lang={item['language']}")
            print()

        if summary["duplicate_work_groups"]:
            print("--- Duplicate Works ---")
            for group in report["duplicate_works"][:5]:
                print(f"  '{group['works'][0]['title']}' x{group['count']} instances")
            print()

        if summary["isbn_violations_count"]:
            print("--- ISBN Violations ---")
            for item in report["isbn_violations"][:10]:
                print(f"  ID={item['id']}  ISBN='{item['isbn13']}'")
            print()

        # Write full report to file
        output_path = Path("exports/frbr_audit_report.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Full report written to: {output_path}")


if __name__ == "__main__":
    main()
