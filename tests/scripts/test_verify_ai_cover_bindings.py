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
"""Tests for scripts/verify_ai_cover_bindings.py.

Verifies detection and repair of mismatched AI-generated cover URLs on FRBR
F3 Manifestations across ISBN mismatches, Item-belonging mismatches, and
Manifestation ID shifts.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db import db
from app.db.core import EntityAuditLog
from app.db.models import Expression, Item, Manifestation, User, Work
from scripts.verify_ai_cover_bindings import (
    inspect_manifestation_cover,
    verify_and_repair_ai_covers,
)


@pytest.fixture
def catalog_setup(app):
    """Fixture providing basic Work, Expression, and User setup."""
    with app.app_context():
        user = User(
            email="testuser@example.com",
            display_name="Test User",
            is_active=True,
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.flush()

        work1 = Work(title="Book One", meta={"authors": ["Author One"]})
        work2 = Work(title="Book Two", meta={"authors": ["Author Two"]})
        db.session.add_all([work1, work2])
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="text")
        expr2 = Expression(work_id=work2.id, content_type="text")
        db.session.add_all([expr1, expr2])
        db.session.flush()

        yield {
            "user": user,
            "work1": work1,
            "work2": work2,
            "expr1": expr1,
            "expr2": expr2,
        }


def test_inspect_and_repair_mismatched_isbn_binding(app, catalog_setup):
    """Manifestation with cover URL for a different ISBN is detected and repaired."""
    with app.app_context():
        expr1 = db.session.get(Expression, catalog_setup["expr1"].id)
        expr2 = db.session.get(Expression, catalog_setup["expr2"].id)

        # Manifestation A has ISBN 9780000000100 but cover for 9789999999999_gemini.jpg
        manif_a = Manifestation(
            expression_id=expr1.id,
            isbn13="9780000000100",
            cover_url="/api/static/covers/9789999999999_gemini.jpg",
            meta={"cover_source": "llm_gemini"},
        )
        # Manifestation B has matching ISBN cover
        manif_b = Manifestation(
            expression_id=expr2.id,
            isbn13="9780000000200",
            cover_url="/api/static/covers/9780000000200_gemini.jpg",
            meta={"cover_source": "llm_gemini"},
        )
        db.session.add_all([manif_a, manif_b])
        db.session.commit()

        # 1. Inspect function direct check
        is_mismatch_a, reason_a = inspect_manifestation_cover(manif_a)
        assert is_mismatch_a is True
        assert "9789999999999" in reason_a
        assert "9780000000100" in reason_a

        is_mismatch_b, reason_b = inspect_manifestation_cover(manif_b)
        assert is_mismatch_b is False
        assert reason_b is None

        # 2. Dry run scan does NOT mutate database
        inspected, mismatches = verify_and_repair_ai_covers(apply_changes=False)
        assert mismatches >= 1

        db.session.refresh(manif_a)
        assert manif_a.cover_url == "/api/static/covers/9789999999999_gemini.jpg"

        # 3. Apply scan repairs the mismatch
        inspected, repaired = verify_and_repair_ai_covers(apply_changes=True)
        assert repaired >= 1

        db.session.refresh(manif_a)
        db.session.refresh(manif_b)

        assert manif_a.cover_url is None
        assert "cover_source" not in (manif_a.meta or {})
        assert manif_b.cover_url == "/api/static/covers/9780000000200_gemini.jpg"

        # Verify EntityAuditLog record
        logs = (
            db.session.execute(
                select(EntityAuditLog).where(
                    EntityAuditLog.entity_type == "manifestation",
                    EntityAuditLog.entity_id == manif_a.id,
                    EntityAuditLog.change_type == "ai_cover_unbind",
                )
            )
            .scalars()
            .all()
        )
        assert len(logs) == 1
        assert logs[0].diff["cover_url"]["old"] == "/api/static/covers/9789999999999_gemini.jpg"
        assert logs[0].diff["cover_url"]["new"] is None


def test_inspect_and_repair_mismatched_item_binding(app, catalog_setup):
    """Manifestation pointing to item_<id> cover belonging to a different manifestation is repaired."""
    with app.app_context():
        user = db.session.get(User, catalog_setup["user"].id)
        expr1 = db.session.get(Expression, catalog_setup["expr1"].id)
        expr2 = db.session.get(Expression, catalog_setup["expr2"].id)

        manif1 = Manifestation(expression_id=expr1.id, isbn13="9781111111111")
        manif2 = Manifestation(expression_id=expr2.id, isbn13="9782222222222")
        db.session.add_all([manif1, manif2])
        db.session.flush()

        item2 = Item(
            manifestation_id=manif2.id,
            owner_id=user.id,
            status="unread",
            collection_status="available",
        )
        db.session.add(item2)
        db.session.commit()

        # Manif1 has a cover keyed for item2 (which belongs to Manif2)
        manif1.cover_url = f"/api/static/covers/item_{item2.id}_gemini.jpg"
        manif1.meta = {"cover_source": "llm_gemini"}
        # Manif2 has the same cover, but for Manif2 it's valid because item2 belongs to Manif2
        manif2.cover_url = f"/api/static/covers/item_{item2.id}_gemini.jpg"
        manif2.meta = {"cover_source": "llm_gemini"}
        db.session.commit()

        is_mismatch1, reason1 = inspect_manifestation_cover(manif1)
        assert is_mismatch1 is True
        assert f"Item #{item2.id}" in reason1
        assert f"Manifestation #{manif2.id}" in reason1

        is_mismatch2, reason2 = inspect_manifestation_cover(manif2)
        assert is_mismatch2 is False
        assert reason2 is None

        # Apply repair
        inspected, repaired = verify_and_repair_ai_covers(apply_changes=True)
        assert repaired >= 1

        db.session.refresh(manif1)
        db.session.refresh(manif2)
        assert manif1.cover_url is None
        assert manif2.cover_url == f"/api/static/covers/item_{item2.id}_gemini.jpg"


def test_inspect_manifestation_id_prefix_mismatch(app, catalog_setup):
    """Manifestation with cover url keyed to another manifestation id is repaired."""
    with app.app_context():
        expr1 = db.session.get(Expression, catalog_setup["expr1"].id)

        manif = Manifestation(
            expression_id=expr1.id,
            isbn13=None,
            cover_url="/api/static/covers/manifestation_9999_openai.jpg",
            meta={"cover_source": "llm_openai"},
        )
        db.session.add(manif)
        db.session.commit()

        is_mismatch, reason = inspect_manifestation_cover(manif)
        assert is_mismatch is True
        assert "Manifestation #9999" in reason

        verify_and_repair_ai_covers(apply_changes=True)
        db.session.refresh(manif)
        assert manif.cover_url is None


def test_non_ai_covers_are_ignored(app, catalog_setup):
    """Standard provider or user covers are ignored by the audit."""
    with app.app_context():
        expr1 = db.session.get(Expression, catalog_setup["expr1"].id)

        manif = Manifestation(
            expression_id=expr1.id,
            isbn13="9780000000001",
            cover_url="https://images.openlibrary.org/b/id/12345-M.jpg",
            meta={"cover_source": "openlibrary"},
        )
        db.session.add(manif)
        db.session.commit()

        is_mismatch, reason = inspect_manifestation_cover(manif)
        assert is_mismatch is False
        assert reason is None


def test_requeue_resets_attached_item_cover_status(app, catalog_setup):
    """--requeue flag resets cover_status to 'pending' on items attached to repaired manifestation."""
    with app.app_context():
        user = db.session.get(User, catalog_setup["user"].id)
        expr1 = db.session.get(Expression, catalog_setup["expr1"].id)

        manif = Manifestation(
            expression_id=expr1.id,
            isbn13="9780000000555",
            cover_url="/api/static/covers/9789999999999_gemini.jpg",
            meta={"cover_source": "llm_gemini"},
        )
        db.session.add(manif)
        db.session.flush()

        item = Item(
            manifestation_id=manif.id,
            owner_id=user.id,
            status="unread",
            collection_status="available",
        )
        item.cover_status = "completed"
        item.cover_url = "/api/static/covers/9789999999999_gemini.jpg"
        db.session.add(item)
        db.session.commit()

        verify_and_repair_ai_covers(apply_changes=True, requeue=True)

        db.session.refresh(manif)
        db.session.refresh(item)
        assert manif.cover_url is None
        assert item.cover_status == "pending"
        assert item.cover_url is None


def test_main_cli_execution(app, monkeypatch):
    """CLI entrypoint main() parses arguments and invokes verify_and_repair_ai_covers."""
    from scripts.verify_ai_cover_bindings import main

    monkeypatch.setattr("sys.argv", ["verify_ai_cover_bindings.py", "--dry-run"])
    with patch("scripts.verify_ai_cover_bindings.verify_and_repair_ai_covers") as mock_repair:
        main()
        assert mock_repair.called
        assert mock_repair.call_args[1]["apply_changes"] is False
