"""Database-level regression tests for security-related model constraints."""

import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from app.db.models import Expression, Item, LoanRequest, Manifestation, User, UserWorkIntent, Work, db


def test_user_visibility_check_constraint_accepts_shared(app):
    with app.app_context():
        user = User(email="shared-visibility@iqoqo.local", google_id="shared-visibility-subject", visibility="shared")
        db.session.add(user)
        db.session.commit()

        assert db.session.get(User, user.id).visibility == "shared"


def test_user_visibility_check_constraint_rejects_unrecognized_value(app):
    with app.app_context():
        db.session.add(User(email="invalid-visibility@iqoqo.local", google_id="invalid-visibility-subject", visibility="unlisted"))

        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_user_auth_method_constraint_rejects_user_without_credentials(app):
    with app.app_context():
        db.session.add(User(email="no-auth-method@iqoqo.local"))

        db.session.info["allow_invalid_user_auth_method"] = True
        with pytest.raises(IntegrityError):
            try:
                db.session.flush()
            finally:
                db.session.info.pop("allow_invalid_user_auth_method", None)
        db.session.rollback()


@pytest.mark.parametrize(
    "credentials",
    [
        {"password_hash": "test-hash"},
        {"google_id": "google-subject-123"},
    ],
)
def test_user_auth_method_constraint_accepts_each_supported_method(app, credentials):
    with app.app_context():
        user = User(email=f"auth-method-{next(iter(credentials))}@iqoqo.local", **credentials)
        db.session.add(user)
        db.session.commit()

        assert db.session.get(User, user.id) is not None


def test_user_model_defines_auth_method_check_constraint():
    check_names = {constraint.name for constraint in User.__table__.constraints if getattr(constraint, "name", None)}
    assert "check_user_auth_method" in check_names


@pytest.mark.parametrize(
    ("status", "collection_status"),
    [("invalid-status", "available"), ("reading", "invalid-collection-status")],
)
def test_item_status_check_constraints_reject_unrecognized_values(app, status, collection_status):
    with app.app_context():
        user = User(email=f"item-check-{status}-{collection_status}@iqoqo.local", google_id=f"item-check-{status}-{collection_status}")
        work = Work(title="Item status constraint work")
        db.session.add_all([user, work])
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text")
        db.session.add(expression)
        db.session.flush()
        manifestation = Manifestation(expression_id=expression.id)
        db.session.add(manifestation)
        db.session.flush()

        db.session.add(
            Item(
                manifestation_id=manifestation.id,
                owner_id=user.id,
                status=status,
                collection_status=collection_status,
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_user_work_intent_status_check_constraint_rejects_unrecognized_value(app):
    with app.app_context():
        user = User(email="invalid-intent-status@iqoqo.local", google_id="invalid-intent-status-subject")
        work = Work(title="Intent status constraint work")
        db.session.add_all([user, work])
        db.session.flush()

        db.session.add(UserWorkIntent(user_id=user.id, work_id=work.id, status="invalid-status"))
        with pytest.raises(IntegrityError):
            db.session.flush()

        db.session.rollback()


def test_postgres_lending_trigger_rejects_direct_self_borrow(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("The self-borrow trigger is PostgreSQL-specific")

        owner = User(email="trigger-owner@iqoqo.local", google_id="trigger-owner-subject")
        borrower = User(email="trigger-borrower@iqoqo.local", google_id="trigger-borrower-subject")
        work = Work(title="Self-borrow trigger work")
        db.session.add_all([owner, borrower, work])
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text")
        db.session.add(expression)
        db.session.flush()
        manifestation = Manifestation(expression_id=expression.id)
        db.session.add(manifestation)
        db.session.flush()
        item = Item(manifestation_id=manifestation.id, owner_id=owner.id, collection_status="available")
        db.session.add(item)
        db.session.commit()

        migration = importlib.import_module("migrations.versions.v0_8_1_lending_self_borrow")

        def run_migration(operation):
            with db.engine.begin() as connection:
                original_op = migration.op
                migration.op = Operations(MigrationContext.configure(connection))
                try:
                    operation()
                finally:
                    migration.op = original_op

        run_migration(migration.upgrade)
        try:
            db.session.add(LoanRequest(item_id=item.id, requester_id=owner.id))
            with pytest.raises(IntegrityError):
                db.session.flush()
            db.session.rollback()

            valid_request = LoanRequest(item_id=item.id, requester_id=borrower.id)
            db.session.add(valid_request)
            db.session.commit()

            valid_request.requester_id = owner.id
            with pytest.raises(IntegrityError):
                db.session.flush()
            db.session.rollback()
        finally:
            db.session.rollback()
            run_migration(migration.downgrade)
