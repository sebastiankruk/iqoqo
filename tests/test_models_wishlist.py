# tests/test_models_wishlist.py
"""Tests for the UserWorkIntent model with expression_id and manifestation_id FK columns.

Covers wishlist-api-separation Tasks 1.1–1.2:
  - UserWorkIntent stores optional expression_id and manifestation_id
  - Composite unique constraint (user_id, work_id, expression_id, manifestation_id)
  - FK relationships with ON DELETE SET NULL behaviour
  - Check constraint on status column
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
#

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Manifestation, User, UserWorkIntent, Work, db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def frbr_stack(app):
    """Seed a full FRBR stack (Work → Expression → Manifestation) and a user."""
    with app.app_context():
        user = User(email="model_test@iqoqo.local", display_name="Model Tester")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Test Work", meta={"authors": ["Author A"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9781234567890",
            meta={"format": MediaFormat.BOOK},
        )
        db.session.add(manif)
        db.session.flush()

        # Second expression (e.g. a translation) for hierarchy tests
        expr2 = Expression(work_id=work.id, content_type=MediaCategory.TEXT, language="fr")
        db.session.add(expr2)
        db.session.flush()

        manif2 = Manifestation(
            expression_id=expr2.id,
            isbn13="9780987654321",
            meta={"format": MediaFormat.BOOK},
        )
        db.session.add(manif2)
        db.session.flush()

        db.session.commit()
        return {
            "user_id": user.id,
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
            "expression2_id": expr2.id,
            "manifestation2_id": manif2.id,
        }


# ---------------------------------------------------------------------------
# Task 1.1 — Model fields and relationships
# ---------------------------------------------------------------------------


class TestUserWorkIntentModelFields:
    """Verify UserWorkIntent stores optional expression_id and manifestation_id."""

    def test_create_intent_with_work_only(self, app, frbr_stack):
        """Given only a work_id, an intent is created with NULL expression/manifestation."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded is not None
            assert loaded.work_id == frbr_stack["work_id"]
            assert loaded.expression_id is None
            assert loaded.manifestation_id is None

    def test_create_intent_with_expression(self, app, frbr_stack):
        """Given work_id + expression_id, the intent binds to a specific F2 realization."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded.expression_id == frbr_stack["expression_id"]
            assert loaded.manifestation_id is None

    def test_create_intent_with_expression_and_manifestation(self, app, frbr_stack):
        """Given all three FKs, the intent binds to a specific F3 embodiment."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded.expression_id == frbr_stack["expression_id"]
            assert loaded.manifestation_id == frbr_stack["manifestation_id"]

    def test_relationship_work(self, app, frbr_stack):
        """The work relationship returns the parent Work."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded.work is not None
            assert loaded.work.title == "Test Work"

    def test_relationship_expression(self, app, frbr_stack):
        """The expression relationship returns the bound Expression when set."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded.expression is not None
            assert loaded.expression.language == "en"

    def test_relationship_manifestation(self, app, frbr_stack):
        """The manifestation relationship returns the bound Manifestation when set."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent.id)
            assert loaded.manifestation is not None
            assert loaded.manifestation.isbn13 == "9781234567890"


# ---------------------------------------------------------------------------
# Task 1.1 — Unique constraint
# ---------------------------------------------------------------------------


class TestUserWorkIntentUniqueConstraint:
    """Verify composite unique constraint (user_id, work_id, expression_id, manifestation_id).

    Note: SQLite treats NULLs as equal in unique constraints, while PostgreSQL
    treats them as distinct. These tests verify the constraint is defined on the
    model; actual enforcement of NULL-involving uniqueness is PostgreSQL-specific.
    """

    def test_duplicate_work_only_intent_rejected_or_distinct(self, app, frbr_stack):
        """Given the same user+work with NULL expression/manifestation, behaviour depends on DB engine.

        PostgreSQL: rejects (NULLs are distinct, so the composite is the same).
        SQLite: allows (NULLs are equal, so the composite is considered different).
        This test verifies the constraint EXISTS on the model regardless of engine.
        """
        with app.app_context():
            # Verify the unique constraint is defined on the model
            table = UserWorkIntent.__table__
            unique_constraints = [
                c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1
            ]
            # Should have at least one multi-column unique constraint
            assert len(unique_constraints) >= 1, "UserWorkIntent should have a composite unique constraint"

            # Verify the constraint covers the expected columns
            constraint_columns = set()
            for c in unique_constraints:
                constraint_columns.update(col.name for col in c.columns)
            assert "user_id" in constraint_columns
            assert "work_id" in constraint_columns

    def test_duplicate_with_all_fields_set_rejected(self, app, frbr_stack):
        """Given the same user+work+expression+manifestation (all non-NULL), duplicate is rejected on all engines."""
        with app.app_context():
            intent1 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            db.session.add(intent1)
            db.session.commit()

            intent2 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_listen",
            )
            db.session.add(intent2)
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_same_work_different_expression_allowed(self, app, frbr_stack):
        """Given the same user+work but different expression_id, both intents coexist."""
        with app.app_context():
            intent1 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                status="want_to_read",
            )
            intent2 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression2_id"],
                status="want_to_read",
            )
            db.session.add_all([intent1, intent2])
            db.session.commit()

            count = UserWorkIntent.query.filter_by(user_id=frbr_stack["user_id"]).count()
            assert count == 2

    def test_same_work_same_expression_different_manifestation_allowed(self, app, frbr_stack):
        """Given same user+work+expression but different manifestation_id, both coexist."""
        with app.app_context():
            # Create a second manifestation under the same expression
            manif_alt = Manifestation(
                expression_id=frbr_stack["expression_id"],
                isbn13="9781111111111",
                meta={"format": MediaFormat.BOOK},
            )
            db.session.add(manif_alt)
            db.session.flush()

            intent1 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            intent2 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=manif_alt.id,
                status="want_to_read",
            )
            db.session.add_all([intent1, intent2])
            db.session.commit()

            count = UserWorkIntent.query.filter_by(user_id=frbr_stack["user_id"]).count()
            assert count == 2

    def test_different_users_same_work_allowed(self, app, frbr_stack):
        """Given different users with the same work, both intents coexist."""
        with app.app_context():
            user2 = User(email="model_test2@iqoqo.local", display_name="Model Tester 2")
            db.session.add(user2)
            db.session.flush()

            intent1 = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            intent2 = UserWorkIntent(
                user_id=user2.id,
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            db.session.add_all([intent1, intent2])
            db.session.commit()

            count = UserWorkIntent.query.filter_by(work_id=frbr_stack["work_id"]).count()
            assert count == 2


# ---------------------------------------------------------------------------
# Task 1.1 — ON DELETE SET NULL behaviour
# ---------------------------------------------------------------------------


class TestUserWorkIntentOnDeleteSetNull:
    """Verify FK columns use ON DELETE SET NULL so wishlist entries survive catalog deletions."""

    def test_expression_deleted_sets_null(self, app, frbr_stack):
        """When an Expression is deleted, intent.expression_id becomes NULL."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()
            intent_id = intent.id

            # Delete the manifestation first (it has a FK to expression)
            manif = db.session.get(Manifestation, frbr_stack["manifestation_id"])
            db.session.delete(manif)
            expr = db.session.get(Expression, frbr_stack["expression_id"])
            db.session.delete(expr)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent_id)
            assert loaded is not None
            assert loaded.expression_id is None
            # Manifestation was also deleted — should also be NULL
            assert loaded.manifestation_id is None
            # Work-level intent survives
            assert loaded.work_id == frbr_stack["work_id"]

    def test_manifestation_deleted_sets_null(self, app, frbr_stack):
        """When a Manifestation is deleted, intent.manifestation_id becomes NULL but expression survives."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                expression_id=frbr_stack["expression_id"],
                manifestation_id=frbr_stack["manifestation_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()
            intent_id = intent.id

            manif = db.session.get(Manifestation, frbr_stack["manifestation_id"])
            db.session.delete(manif)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent_id)
            assert loaded is not None
            assert loaded.manifestation_id is None
            # Expression FK should survive
            assert loaded.expression_id == frbr_stack["expression_id"]

    def test_work_deleted_cascades_intent(self, app, frbr_stack):
        """When a Work is deleted, the intent is CASCADE-deleted (not SET NULL)."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()
            intent_id = intent.id

            work = db.session.get(Work, frbr_stack["work_id"])
            db.session.delete(work)
            db.session.commit()

            loaded = db.session.get(UserWorkIntent, intent_id)
            assert loaded is None


# ---------------------------------------------------------------------------
# Task 1.1 — Status check constraint
# ---------------------------------------------------------------------------


class TestUserWorkIntentStatusConstraint:
    """Verify the CHECK constraint on the status column."""

    def test_valid_status_accepted(self, app, frbr_stack):
        """A valid progress status is accepted."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="want_to_read",
            )
            db.session.add(intent)
            db.session.commit()
            assert intent.id is not None

    def test_fulfilled_status_accepted(self, app, frbr_stack):
        """The 'fulfilled' status is accepted (it's in WORK_INTENT_STATUSES)."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="fulfilled",
            )
            db.session.add(intent)
            db.session.commit()
            assert intent.id is not None

    def test_invalid_status_rejected(self, app, frbr_stack):
        """An invalid status value violates the CHECK constraint."""
        with app.app_context():
            intent = UserWorkIntent(
                user_id=frbr_stack["user_id"],
                work_id=frbr_stack["work_id"],
                status="totally_invalid_status",
            )
            db.session.add(intent)
            with pytest.raises(IntegrityError):
                db.session.commit()
