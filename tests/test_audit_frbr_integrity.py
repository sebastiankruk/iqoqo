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
"""Unit and regression tests for scripts/audit_frbr_integrity.py."""

from app.db import db
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import User
from scripts.audit_frbr_integrity import (
    run_audit,
    validate_isbn10_checksum,
    validate_isbn13_checksum,
)


def test_validate_isbn_checksums() -> None:
    """Ensure checksum calculation properly validates ISBN-10 and ISBN-13 check digits."""
    # Valid ISBN-10 (standard and check digit 'X')
    assert validate_isbn10_checksum("0-306-40615-2") is True
    assert validate_isbn10_checksum("0306406152") is True
    assert validate_isbn10_checksum("0-8044-2957-X") is True
    assert validate_isbn10_checksum("080442957X") is True

    # Invalid ISBN-10
    assert validate_isbn10_checksum("0-306-40615-5") is False
    assert validate_isbn10_checksum("12345") is False

    # Valid ISBN-13
    assert validate_isbn13_checksum("978-0-306-40615-7") is True
    assert validate_isbn13_checksum("9780306406157") is True
    assert validate_isbn13_checksum("978-0-13-110362-7") is True

    # Invalid ISBN-13
    assert validate_isbn13_checksum("978-0-306-40615-9") is False
    assert validate_isbn13_checksum("978123456789") is False


def test_audit_clean_hierarchy(app) -> None:
    """Ensure a properly structured catalog yields zero audit violations."""
    with app.app_context():
        user = User(email="test_curator@iqoqo.local", display_name="Curator")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Dune", meta={"authors": ["Frank Herbert"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780441172719",
            publisher="Ace Books",
            meta={},
        )
        db.session.add(manif)
        db.session.flush()

        item = Item(owner_id=user.id, manifestation_id=manif.id, status="available")
        db.session.add(item)
        db.session.commit()

        report = run_audit()
        assert report["summary"]["total_violations"] == 0
        assert report["summary"]["orphan_expressions_count"] == 0
        assert report["summary"]["orphan_manifestations_count"] == 0
        assert report["summary"]["orphan_items_count"] == 0
        assert report["summary"]["duplicate_work_clusters"] == 0
        assert report["summary"]["duplicate_manifestation_clusters"] == 0
        assert report["summary"]["isbn_violations_count"] == 0


def test_audit_orphan_detection(app) -> None:
    """Ensure audit flags orphaned Expressions, Manifestations, and Items."""
    with app.app_context():
        user = User(email="orphan_owner@iqoqo.local", display_name="Owner")
        db.session.add(user)
        db.session.flush()

        # Expression referencing non-existent Work (999999)
        orphan_expr = Expression(work_id=999999, content_type="text", language="en")
        db.session.add(orphan_expr)

        # Manifestation referencing non-existent Expression (999999)
        orphan_manif = Manifestation(expression_id=999999, isbn13=None)
        db.session.add(orphan_manif)

        # Item referencing non-existent Manifestation (999999)
        orphan_item = Item(owner_id=user.id, manifestation_id=999999, status="lost")
        db.session.add(orphan_item)
        db.session.commit()

        report = run_audit()
        assert report["summary"]["orphan_expressions_count"] >= 1
        assert report["summary"]["orphan_manifestations_count"] >= 1
        assert report["summary"]["orphan_items_count"] >= 1

        expr_ids = [e["id"] for e in report["orphans"]["expressions"]]
        assert orphan_expr.id in expr_ids

        manif_ids = [m["id"] for m in report["orphans"]["manifestations"]]
        assert orphan_manif.id in manif_ids

        item_ids = [i["id"] for i in report["orphans"]["items"]]
        assert orphan_item.id in item_ids


def test_audit_duplicate_detection(app) -> None:
    """Ensure duplicate Works and duplicate Manifestations are flagged."""
    with app.app_context():
        # Duplicate works: identical normalized title and authors
        w1 = Work(title="Neuromancer", meta={"authors": ["William Gibson"]})
        w2 = Work(title=" neuromancer ", meta={"authors": ["william gibson"]})
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type="text")
        e2 = Expression(work_id=w2.id, content_type="text")
        db.session.add_all([e1, e2])
        db.session.flush()

        # Duplicate manifestations: identical normalized ISBN-13
        m1 = Manifestation(expression_id=e1.id, isbn13="9780441569595")
        m2 = Manifestation(expression_id=e2.id, isbn13="978-0-441-56959-5")
        db.session.add_all([m1, m2])
        db.session.commit()

        report = run_audit()
        assert report["summary"]["duplicate_work_clusters"] >= 1
        assert report["summary"]["duplicate_manifestation_clusters"] >= 1

        # Verify duplicate work clusters contain both w1 and w2
        found_work_cluster = False
        for cluster in report["duplicates"]["works"]:
            ids = [entity["id"] for entity in cluster["entities"]]
            if w1.id in ids and w2.id in ids:
                found_work_cluster = True
                break
        assert found_work_cluster is True

        # Verify duplicate manifestation clusters contain both m1 and m2
        found_manif_cluster = False
        for cluster in report["duplicates"]["manifestations"]:
            ids = [entity["id"] for entity in cluster["entities"]]
            if m1.id in ids and m2.id in ids:
                found_manif_cluster = True
                break
        assert found_manif_cluster is True


def test_audit_isbn_violations(app) -> None:
    """Ensure ISBN format, check digit, and misplaced Work-level ISBNs are detected."""
    with app.app_context():
        # Work with misplaced ISBN in meta
        work_with_isbn = Work(
            title="Foundation",
            meta={"isbn13": "9780553293357", "authors": ["Isaac Asimov"]},
        )
        db.session.add(work_with_isbn)
        db.session.flush()

        expr = Expression(work_id=work_with_isbn.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        # Manifestation with ISBN-10 (unnormalized)
        m_isbn10 = Manifestation(expression_id=expr.id, isbn13="0553293354")
        # Manifestation with invalid 13-digit checksum
        m_bad_checksum = Manifestation(expression_id=expr.id, isbn13="9780553293350")
        # Manifestation with invalid length
        m_bad_length = Manifestation(expression_id=expr.id, isbn13="12345")

        db.session.add_all([m_isbn10, m_bad_checksum, m_bad_length])
        db.session.commit()

        report = run_audit()
        violations = report["isbn_violations"]
        assert len(violations) >= 4

        violation_types = {v["violation"] for v in violations}
        assert "work_level_isbn" in violation_types
        assert "isbn10_unnormalized" in violation_types
        assert "invalid_checksum_isbn13" in violation_types
        assert "invalid_length" in violation_types
