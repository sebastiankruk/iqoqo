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
"""Migration index names must match what the ORM models generate.

`index=True` on a schema-qualified column produces a schema-prefixed index
name, so a migration that hardcodes the schema-less name agrees with the model
on SQLite and disagrees on PostgreSQL. SQLite cannot see the difference; a
fully-migrated PostgreSQL database shows it as permanent autogenerate noise
that proposes renaming indexes which are already correct.

The test is skipped unless the isolated E2E PostgreSQL service is reachable,
since SQLite cannot reproduce the divergence at all.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Administrative connection URL for the PostgreSQL instance these tests run
#: against. Overridable so CI can point at its own service container instead of
#: requiring the local E2E stack to be up -- which is what left this suite
#: running on exactly one maintainer's laptop and skipped everywhere else.
E2E_URL = os.environ.get(
    "IQOQO_TEST_PG_ADMIN_URL",
    "postgresql://iqoqo_e2e:e2e_local_only@127.0.0.1:55432/",
)


def _e2e_available() -> bool:
    """Whether the configured PostgreSQL service accepts connections."""
    try:
        engine = sa.create_engine(E2E_URL + "postgres", connect_args={"connect_timeout": 2})
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _e2e_available(),
    reason=("needs a PostgreSQL instance; run `make test-e2e-db-up` locally, or set " "IQOQO_TEST_PG_ADMIN_URL to point at one"),
)


def _fresh_database(name: str) -> str:
    """Create an empty database and return its URL.

    @param name: Database name to create.
    @returns: A connection URL for the new database.
    """
    admin = sa.create_engine(E2E_URL + "postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}"'))
        conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
    admin.dispose()
    return E2E_URL + name


def _drop_database(url: str, name: str) -> None:
    """Drop the scratch database.

    @param url: URL of the scratch database, used to locate the server.
    @param name: Database name to drop.
    """
    admin = sa.create_engine(url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def _index_names(url: str, table: str, schema: str) -> set[str]:
    """Read the live index names on a table.

    @param url: Database URL.
    @param table: Unqualified table name.
    @param schema: Schema name.
    @returns: The index names present.
    """
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT indexname FROM pg_indexes WHERE schemaname = :s AND tablename = :t"),
            {"s": schema, "t": table},
        )
        names = {r[0] for r in rows}
    engine.dispose()
    return names


def _flask_db(url: str, *args: str) -> str:
    """Run `flask db` against ``url`` in a subprocess.

    The chain has to go through `flask db upgrade`, not the bare Alembic API:
    `migrations/env.py` reads `current_app.extensions["migrate"]`, so a
    standalone `command.upgrade()` finds no Flask app and the migrations run
    against SQLite instead -- which is precisely the dialect that cannot
    reproduce this bug.

    @param url: Database URL to operate on.
    @param args: Arguments to pass to `flask db`.
    @returns: The command's combined output.
    """
    env = {**os.environ, "DATABASE_URL": url, "FLASK_APP": "run.py"}
    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, f"flask db {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout + result.stderr


def _migrated() -> str:
    """Build a fresh database, migrate it to head, and return its URL.

    Function-scoped rather than a module-scoped fixture: the downgrade tests
    mutate the index names, and re-running the ~30s chain per test keeps each
    one independent of execution order.

    @returns: The migrated database URL.
    """
    url = _fresh_database("c18_index_names")
    _flask_db(url, "upgrade")
    return url


def test_fk_indexes_use_the_schema_prefixed_names() -> None:
    """The manifestation FK index carries the inventory schema prefix."""
    url = _migrated()
    try:
        names = _index_names(url, "items", "inventory")
        assert "ix_inventory_items_manifestation_id" in names, f"got {sorted(names)}"
        assert "ix_items_manifestation_id" not in names, "the schema-less name survived the rename"
    finally:
        _drop_database(url, "c18_index_names")


def test_roadmap_user_index_uses_the_catalog_prefix() -> None:
    """The roadmap user index carries the catalog schema prefix."""
    url = _migrated()
    try:
        names = _index_names(url, "reading_roadmaps", "catalog")
        assert "ix_catalog_reading_roadmaps_user_id" in names, f"got {sorted(names)}"
        assert "ix_reading_roadmaps_user_id" not in names, "the schema-less name survived the rename"
    finally:
        _drop_database(url, "c18_index_names")


def test_rename_is_idempotent() -> None:
    """Re-running the rename must not fail on an already-renamed index.

    An operator who applied it by hand, or a database restored from a dump that
    already carries the new names, should not hit "relation already exists".
    """
    url = _migrated()
    try:
        _flask_db(url, "upgrade", "v0_8_2_fk_index_names")

        names = _index_names(url, "items", "inventory")
        assert "ix_inventory_items_manifestation_id" in names
        assert "ix_items_manifestation_id" not in names
    finally:
        _drop_database(url, "c18_index_names")


def test_downgrade_restores_the_bare_names_to_a_known_revision() -> None:
    """The downgrade is deterministic when targeting the revision explicitly.

    Naming the target keeps this independent of whatever sits below it, which is
    what makes it a test of *this* migration rather than of its neighbour.
    """
    url = _migrated()
    try:
        _flask_db(url, "downgrade", "v0_8_2_fk_indexes_and_quantity")

        assert "ix_items_manifestation_id" in _index_names(url, "items", "inventory")
        assert "ix_reading_roadmaps_user_id" in _index_names(url, "reading_roadmaps", "catalog")
    finally:
        _drop_database(url, "c18_index_names")


def test_downgrade_one_step_only_renames_back() -> None:
    """A single downgrade reverses the rename and nothing more.

    Note this is *not* the same as "downgrading twice". `flask db downgrade`
    with no target steps to the previous revision, so the second invocation
    lands on `v0_8_2_fk_indexes_and_quantity`, whose own downgrade drops both
    indexes outright. That is correct behaviour, and it is why the re-upgrade
    test below re-applies the chain rather than expecting the index to persist.
    """
    url = _migrated()
    try:
        # Target the revision by name rather than stepping once from head.
        # `downgrade` with no argument means "one revision back", which was
        # `v0_8_2_fk_index_names` when that was the head -- but head has since
        # moved on, so a bare downgrade would now only undo the newer revision
        # and leave the rename in place. Naming the target states the intent.
        _flask_db(url, "downgrade", "v0_8_2_fk_indexes_and_quantity")

        assert "ix_items_manifestation_id" in _index_names(url, "items", "inventory")
        assert "ix_reading_roadmaps_user_id" in _index_names(url, "reading_roadmaps", "catalog")
    finally:
        _drop_database(url, "c18_index_names")


def test_downgrade_past_the_rename_is_clean() -> None:
    """Stepping below the rename revision must not raise.

    The previous revision drops the indexes unconditionally, so this exercises
    the boundary where the rename's downgrade must find nothing left to undo.
    """
    url = _migrated()
    try:
        _flask_db(url, "downgrade")
        _flask_db(url, "downgrade")

        assert "ix_inventory_items_manifestation_id" not in _index_names(url, "items", "inventory")
    finally:
        _drop_database(url, "c18_index_names")


def test_reupgrade_after_downgrade_converges() -> None:
    """Upgrading again after a downgrade restores the schema-prefixed names.

    The full round trip is what a real rollback-then-forward operation does, and
    it is where an asymmetric downgrade would show up.
    """
    url = _migrated()
    try:
        _flask_db(url, "downgrade")
        _flask_db(url, "upgrade")

        assert "ix_inventory_items_manifestation_id" in _index_names(url, "items", "inventory")
        assert "ix_catalog_reading_roadmaps_user_id" in _index_names(url, "reading_roadmaps", "catalog")
    finally:
        _drop_database(url, "c18_index_names")


_MODEL_INDEX_PROBE = """
import json, os, sys
os.environ["DATABASE_URL"] = sys.argv[1]
from app import create_app
from flask import current_app

app = create_app()
with app.app_context():
    md = current_app.extensions["migrate"].db.metadata
    out = {}
    for name, table in md.tables.items():
        if table.indexes:
            out[name] = sorted(ix.name for ix in table.indexes)
    print("PROBE" + json.dumps(out))
"""


def _model_index_names(url: str) -> dict[str, list[str]]:
    """Ask a fresh process what the models call every index.

    The model classes decide their schema qualification **at import time** from
    `DATABASE_URL`. `tests/conftest.py` forces `sqlite:///:memory:` unless
    `ENABLE_FTS_TESTS=true`, so by the time this file's tests run, `app.db.core`
    has already been imported with schema-less models and every index name lacks
    the prefix. Comparing against those would be comparing the wrong thing.

    @param url: PostgreSQL URL, so the subprocess binds models to schemas.
    @returns: Index names per qualified table, as the models generate them.
    """
    result = subprocess.run(
        [sys.executable, "-c", _MODEL_INDEX_PROBE, url],
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": url, "ENABLE_FTS_TESTS": "true"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"model probe failed:\n{result.stdout}\n{result.stderr}"
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("PROBE")), None)
    assert line, f"probe produced no output:\n{result.stdout}\n{result.stderr}"
    return json.loads(line[len("PROBE") :])


def _live_indexes(url: str) -> dict[str, set[str]]:
    """Read every live index, keyed by qualified table name.

    @param url: Database URL.
    @returns: Index names per qualified table.
    """
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT schemaname || '.' || tablename, indexname FROM pg_indexes "
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
            )
        )
        out: dict[str, set[str]] = {}
        for table, index in rows:
            out.setdefault(table, set()).add(index)
    engine.dispose()
    return out


def test_every_model_index_exists_under_exactly_that_name() -> None:
    """No model-declared index is missing from a fully-migrated database.

    This is the assertion that catches the whole class of bug, not just the two
    indexes the migration was written for. Before the rename the models wanted
    `ix_inventory_items_manifestation_id` while the database carried
    `ix_items_manifestation_id`, so `flask db revision --autogenerate` proposed
    renaming all three indexes on `inventory.items` -- including the two that
    were already correct -- and could never converge.

    @returns: Nothing; raises on the first mismatch.
    """
    url = _migrated()
    try:
        model = _model_index_names(url)
        live = _live_indexes(url)

        missing: dict[str, list[str]] = {}
        for table, indexes in model.items():
            absent = sorted(set(indexes) - live.get(table, set()))
            if absent:
                missing[table] = absent

        assert not missing, "models declare indexes the database lacks:\n" + "\n".join(
            f"  {table}: {names}" for table, names in sorted(missing.items())
        )
    finally:
        _drop_database(url, "c18_index_names")


def test_the_index_name_check_covers_the_known_renames() -> None:
    """Pin the three specific divergences this migration corrects.

    The general test above would pass vacuously if the probe silently returned
    nothing, so name them explicitly.
    """
    url = _migrated()
    try:
        assert "ix_inventory_items_manifestation_id" in _index_names(url, "items", "inventory")
        assert "ix_catalog_reading_roadmaps_user_id" in _index_names(url, "reading_roadmaps", "catalog")
        assert "ix_config_instance_settings_key" in _index_names(url, "instance_settings", "config")

        assert "ix_items_manifestation_id" not in _index_names(url, "items", "inventory")
        assert "ix_reading_roadmaps_user_id" not in _index_names(url, "reading_roadmaps", "catalog")
        assert "ix_catalog_instance_settings_key" not in _index_names(url, "instance_settings", "config")
    finally:
        _drop_database(url, "c18_index_names")


def test_index_name_agreement_is_load_bearing() -> None:
    """Restoring the bare names must break the agreement above.

    Without this, `test_model_and_database_index_names_agree` could pass for the
    wrong reason -- for instance if the probe silently returned an empty set.
    """
    url = _migrated()
    try:
        assert _model_index_names(url)["inventory.items"], "the model probe returned no indexes"

        engine = sa.create_engine(url)
        with engine.connect() as conn:
            conn.execute(sa.text('ALTER INDEX "inventory"."ix_inventory_items_manifestation_id" RENAME TO "ix_items_manifestation_id"'))
            conn.commit()
        engine.dispose()

        model = set(_model_index_names(url)["inventory.items"])
        live = _index_names(url, "items", "inventory")
        assert model - live, "reintroducing the bare name produced no mismatch, so the check is vacuous"
    finally:
        _drop_database(url, "c18_index_names")
