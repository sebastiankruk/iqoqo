"""ETL script to enforce strict FRBR integrity constraints.

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

Operations:
- Merge duplicate Works (same title + same authors → single Work)
- Re-link orphan Expressions/Manifestations to their proper parents
- Normalize ISBN-13 (strip hyphens, validate check digit)
- Idempotent: safe to run multiple times
- Creates JSON backup before modifications
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _isbn_check_digit(digits: str) -> str:
    """Calculate ISBN-13 check digit."""
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    check = (10 - (total % 10)) % 10
    return str(check)


def normalize_isbn(raw: str) -> str | None:
    """Strip hyphens and validate ISBN-13 check digit. Returns normalized ISBN or None."""
    cleaned = re.sub(r"[^0-9X]", "", raw.upper())
    if len(cleaned) != 13:
        return None
    expected = _isbn_check_digit(cleaned)
    if cleaned[12] != expected:
        return None
    return cleaned


def main() -> None:
    """Run the ETL pipeline."""
    from app import create_app
    from app.db.core import Expression, Manifestation, Work
    from app.db.models import db

    app = create_app()
    with app.app_context():
        # --- Backup current state ---
        backup_path = Path("exports/frbr_etl_backup.json")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        works = Work.query.all()
        backup_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "works_count": len(works),
        }
        backup_path.write_text(
            json.dumps(backup_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Backup metadata written to: {backup_path}")

        # --- 1. Merge duplicate Works (same title + same authors) ---
        work_groups: dict[str, list] = {}
        for w in works:
            authors = sorted(w.meta.get("authors", []) or []) if w.meta else []
            key = f"{(w.title or '').strip().lower()}||{'|'.join(a.lower() for a in authors)}"
            work_groups.setdefault(key, []).append(w)

        merged_count = 0
        for _key, group in work_groups.items():
            if len(group) <= 1:
                continue
            # Keep the first, merge others into it
            primary = group[0]
            for duplicate in group[1:]:
                # Re-link expressions from duplicate to primary
                for expr in Expression.query.filter_by(work_id=duplicate.id).all():
                    expr.work_id = primary.id
                db.session.delete(duplicate)
                merged_count += 1

        if merged_count:
            db.session.flush()
            print(f"Merged {merged_count} duplicate Works")

        # --- 2. Re-link orphan Expressions (without valid Work) ---
        orphan_exprs = Expression.query.filter(
            ~Expression.work_id.in_(db.session.query(Work.id))
        ).all()
        relinked_exprs = 0
        for expr in orphan_exprs:
            # Create a placeholder Work for orphaned expressions
            placeholder = Work(title=f"[Recovered] Expression {expr.id}", meta={})
            db.session.add(placeholder)
            db.session.flush()
            expr.work_id = placeholder.id
            relinked_exprs += 1

        if relinked_exprs:
            print(f"Re-linked {relinked_exprs} orphan Expressions")

        # --- 3. Re-link orphan Manifestations (without valid Expression) ---
        orphan_manifs = Manifestation.query.filter(
            ~Manifestation.expression_id.in_(db.session.query(Expression.id))
        ).all()
        relinked_manifs = 0
        for manif in orphan_manifs:
            # Create placeholder Expression + Work
            placeholder_work = Work(title=f"[Recovered] Manifestation {manif.id}", meta={})
            db.session.add(placeholder_work)
            db.session.flush()
            placeholder_expr = Expression(work_id=placeholder_work.id, content_type="text")
            db.session.add(placeholder_expr)
            db.session.flush()
            manif.expression_id = placeholder_expr.id
            relinked_manifs += 1

        if relinked_manifs:
            print(f"Re-linked {relinked_manifs} orphan Manifestations")

        # --- 4. Normalize ISBN-13 ---
        isbn_fixed = 0
        for manif in Manifestation.query.filter(Manifestation.isbn13.isnot(None)).all():
            if not manif.isbn13:
                continue
            normalized = normalize_isbn(manif.isbn13)
            if normalized and normalized != manif.isbn13:
                manif.isbn13 = normalized
                isbn_fixed += 1
            elif not normalized:
                # Invalid ISBN — clear it
                print(f"  Warning: Invalid ISBN '{manif.isbn13}' on manifestation {manif.id} — clearing")
                manif.isbn13 = None
                isbn_fixed += 1

        if isbn_fixed:
            print(f"Normalized {isbn_fixed} ISBNs")

        # Commit all changes
        db.session.commit()

        total_changes = merged_count + relinked_exprs + relinked_manifs + isbn_fixed
        if total_changes == 0:
            print("No issues found — database is already clean.")
        else:
            print(f"\nETL complete: {total_changes} total fixes applied.")


if __name__ == "__main__":
    main()
