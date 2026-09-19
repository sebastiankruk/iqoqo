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
"""Unit and regression tests for scripts/etl_frbr_strict.py."""

import json
from pathlib import Path

from sqlalchemy import select

from app.db import db
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import User
from scripts.audit_frbr_integrity import run_audit
from scripts.etl_frbr_strict import (
    create_pre_execution_backup,
    isbn10_to_isbn13,
    normalize_to_isbn13,
    run_etl_pipeline,
)


def test_isbn_normalization_helpers() -> None:
    """Verify ISBN-10 to ISBN-13 conversion and general ISBN-13 normalization."""
    # ISBN-10 to ISBN-13 conversion
    assert isbn10_to_isbn13("0-306-40615-2") == "9780306406157"
    assert isbn10_to_isbn13("080442957X") == "9780804429573"
    assert isbn10_to_isbn13("invalid") is None
    assert isbn10_to_isbn13("1234567890") is None  # Invalid check digit

    # General normalize_to_isbn13
    assert normalize_to_isbn13("0-306-40615-2") == "9780306406157"
    assert normalize_to_isbn13("978-0-306-40615-7") == "9780306406157"
    assert normalize_to_isbn13("9780306406157") == "9780306406157"
    assert normalize_to_isbn13("978-0-306-40615-9") is None  # Bad checksum


def test_etl_backup_creation(app, tmp_path: Path) -> None:
    """Verify pre-execution backup generates a valid readable JSON snapshot."""
    with app.app_context():
        user = User(email="backup_test@iqoqo.local", display_name="Tester")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Backup Book", meta={"authors": ["Author"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780306406157")
        db.session.add(manif)
        db.session.flush()

        item = Item(owner_id=user.id, manifestation_id=manif.id, status="available")
        db.session.add(item)
        db.session.commit()

        backup_file = create_pre_execution_backup(tmp_path)
        assert backup_file.exists()
        assert backup_file.stat().st_size > 0

        data = json.loads(backup_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert data["counts"]["works"] >= 1
        assert data["counts"]["items"] >= 1


def test_etl_dry_run(app) -> None:
    """Verify that --dry-run simulates changes without modifying the database."""
    with app.app_context():
        user = User(email="dryrun_user@iqoqo.local", display_name="DryRun")
        db.session.add(user)
        db.session.flush()

        # Two works with identical titles
        w1 = Work(title="Simulated Work", meta={"authors": ["Tester"]})
        w2 = Work(title="Simulated Work", meta={"authors": ["Tester"]})
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type="text")
        e2 = Expression(work_id=w2.id, content_type="text")
        db.session.add_all([e1, e2])
        db.session.commit()

        stats = run_etl_pipeline(dry_run=True, skip_backup=True)
        assert stats["reconciled_works"] >= 1
        assert stats["reparented_expressions"] >= 1

        # In dry run, w1 and w2 must still both exist
        remaining_works = db.session.execute(select(Work).where(Work.id.in_([w1.id, w2.id]))).scalars().all()
        assert len(remaining_works) == 2


def test_etl_manifestation_merging_and_item_reparenting(app) -> None:
    """Verify duplicate Manifestations merge and reparent associated physical Items."""
    with app.app_context():
        user = User(email="reparent_user@iqoqo.local", display_name="Reparent")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Shared Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        # Duplicate manifestations: one unhyphenated, one hyphenated
        m1 = Manifestation(expression_id=expr.id, isbn13="9780441172719", publisher="Ace")
        m2 = Manifestation(expression_id=expr.id, isbn13="978-0-441-17271-9", publisher="Ace", meta={"extra": "info"})
        db.session.add_all([m1, m2])
        db.session.flush()

        item1 = Item(owner_id=user.id, manifestation_id=m1.id, status="available")
        item2 = Item(owner_id=user.id, manifestation_id=m2.id, status="available")
        db.session.add_all([item1, item2])
        db.session.commit()

        stats = run_etl_pipeline(dry_run=False, skip_backup=True)
        assert stats["reconciled_manifestations"] >= 1
        assert stats["reparented_items"] >= 1

        # Only one manifestation should remain
        remaining = db.session.execute(select(Manifestation).where(Manifestation.id.in_([m1.id, m2.id]))).scalars().all()
        assert len(remaining) == 1
        canonical = remaining[0]

        # Both items must now point to the canonical manifestation
        db.session.refresh(item1)
        db.session.refresh(item2)
        assert item1.manifestation_id == canonical.id
        assert item2.manifestation_id == canonical.id


def test_etl_work_duplicate_merging(app) -> None:
    """Verify duplicate Works merge and expressions are reparented to the canonical record."""
    with app.app_context():
        w1 = Work(title="Hyperion", meta={"authors": ["Dan Simmons"], "genre": "SciFi"})
        w2 = Work(title=" hyperion ", meta={"authors": ["dan simmons"], "theme": "Pilgrimage"})
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type="text")
        e2 = Expression(work_id=w2.id, content_type="text")
        db.session.add_all([e1, e2])
        db.session.commit()

        stats = run_etl_pipeline(dry_run=False, skip_backup=True)
        assert stats["reconciled_works"] >= 1
        assert stats["reparented_expressions"] >= 1

        remaining_works = db.session.execute(select(Work).where(Work.id.in_([w1.id, w2.id]))).scalars().all()
        assert len(remaining_works) == 1
        canonical_work = remaining_works[0]

        db.session.refresh(e1)
        db.session.refresh(e2)
        assert e1.work_id == canonical_work.id
        assert e2.work_id == canonical_work.id


def test_etl_relocate_work_isbn_and_idempotence(app) -> None:
    """Verify Work-level ISBN relocation to child Manifestation and idempotent consecutive runs."""
    with app.app_context():
        # Work with misplaced ISBN-10
        work = Work(
            title="Solaris",
            meta={"isbn": "0-15-602760-7", "authors": ["Stanislaw Lem"]},
        )
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13=None)
        db.session.add(manif)
        db.session.commit()

        # First run: relocates and normalizes ISBN to 13 digits
        stats1 = run_etl_pipeline(dry_run=False, skip_backup=True)
        assert stats1["relocated_work_isbns"] >= 1

        db.session.refresh(work)
        db.session.refresh(manif)

        assert "isbn" not in (work.meta or {})
        assert manif.isbn13 == "9780156027601"

        # Second run: must be completely idempotent (0 changes)
        stats2 = run_etl_pipeline(dry_run=False, skip_backup=True)
        assert stats2["reconciled_works"] == 0
        assert stats2["reconciled_manifestations"] == 0
        assert stats2["reparented_items"] == 0
        assert stats2["reparented_expressions"] == 0
        assert stats2["normalized_isbns"] == 0
        assert stats2["relocated_work_isbns"] == 0

        # Audit must also report 0 violations for these entities
        audit_report = run_audit()
        assert audit_report["summary"]["total_violations"] == 0
