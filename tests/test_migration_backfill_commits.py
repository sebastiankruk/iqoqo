"""Tests for migration e3f891ab45c2 batch-commit ETL backfill (OpenSpec v0716-alembic-migration-sre).

Pins:
- Explicit ``connection.commit()`` after each backfill batch (incremental lock release).
- Configurable batch size via the ``_BACKFILL_BATCH_SIZE`` module constant.
- Idempotency: re-running the migration skips already-processed rows and issues no commits.
- Clean run against an empty database (nothing to backfill, schema untouched).
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

# pylint: disable=redefined-outer-name,import-outside-toplevel

from importlib import import_module

import sqlalchemy as sa
from sqlalchemy.engine import Connection

migration = import_module("migrations.versions.e3f891ab45c2_add_relational_frbr_columns_and_etl_backfill")


def _run_upgrade(connection) -> None:
    """Execute the migration's upgrade() bound to the given connection."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    ctx = MigrationContext.configure(connection)
    original_op = migration.op
    migration.op = Operations(ctx)  # type: ignore[attr-defined]
    try:
        migration.upgrade()
    finally:
        migration.op = original_op  # type: ignore[attr-defined]


def _catalog_schema(engine) -> str | None:
    """Return the catalog schema name on PostgreSQL, None on SQLite."""
    return "catalog" if engine.dialect.name == "postgresql" else None


def _qualified(table: str, schema: str | None) -> str:
    return f"{schema}.{table}" if schema else table


def test_backfill_migration_runs_cleanly_on_empty_database(app) -> None:
    """upgrade() completes without error when there is nothing to backfill."""
    from app.db.models import db

    with app.app_context():
        schema = _catalog_schema(db.engine)
        with db.engine.connect() as conn:
            _run_upgrade(conn)
            conn.commit()

        inspector = sa.inspect(db.engine)
        work_cols = {col["name"] for col in inspector.get_columns("works", schema=schema)}
        assert {"sort_title", "raw_payload"} <= work_cols
        manif_cols = {col["name"] for col in inspector.get_columns("manifestations", schema=schema)}
        assert {"format", "label", "barcode", "catalog_number", "raw_payload"} <= manif_cols


def test_backfill_commits_after_each_batch_and_skips_processed_rows(app, monkeypatch) -> None:
    """Batch size of 1 forces one explicit commit per row; a re-run commits nothing."""
    from app.db.models import Expression, Manifestation, Work, db

    with app.app_context():
        schema = _catalog_schema(db.engine)
        works_table = _qualified("works", schema)
        manif_table = _qualified("manifestations", schema)

        # Seed rows with NULL relational columns (service layer intentionally bypassed).
        works = [Work(title=f"The Batched Title {i}", meta={}) for i in range(3)]
        db.session.add_all(works)
        db.session.flush()
        for work in works:
            expr = Expression(work_id=work.id, content_type="text", meta={})
            db.session.add(expr)
            db.session.flush()
            db.session.add(
                Manifestation(
                    expression_id=expr.id,
                    meta={"format": "dvd", "label": "Test Label", "barcode": "123456789012", "catalog_number": "TL-1"},
                )
            )
        db.session.commit()
        db.session.remove()

        # Force a batch size of 1 so every row is processed in its own batch.
        monkeypatch.setattr(migration, "_BACKFILL_BATCH_SIZE", 1)

        commit_count = 0
        original_commit = Connection.commit

        def counting_commit(self) -> None:
            nonlocal commit_count
            commit_count += 1
            return original_commit(self)

        monkeypatch.setattr(Connection, "commit", counting_commit)

        with db.engine.connect() as conn:
            _run_upgrade(conn)
            conn.commit()

        # 3 works + 3 manifestations at batch size 1 => at least 6 explicit batch commits
        # (the trailing conn.commit() above may add one more).
        assert commit_count >= 6

        with db.engine.connect() as conn:
            remaining_works = conn.execute(
                sa.text(f"SELECT COUNT(*) FROM {works_table} WHERE sort_title IS NULL AND title IS NOT NULL")
            ).scalar_one()
            unprocessed_manifs = conn.execute(
                sa.text(
                    f"SELECT COUNT(*) FROM {manif_table} WHERE meta IS NOT NULL "
                    "AND format IS NULL AND label IS NULL AND barcode IS NULL AND catalog_number IS NULL"
                )
            ).scalar_one()
        assert remaining_works == 0
        assert unprocessed_manifs == 0

        db.session.expire_all()
        for work in Work.query.all():
            assert work.sort_title
        for manif in Manifestation.query.all():
            assert manif.format == "dvd"
            assert manif.label == "Test Label"
            assert manif.barcode == "123456789012"
            assert manif.catalog_number == "TL-1"

        # Idempotency: a second run finds nothing to process and issues no batch commits.
        commit_count = 0
        with db.engine.connect() as conn:
            _run_upgrade(conn)
        assert commit_count == 0
