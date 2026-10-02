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
"""C18 1.7: the legacy-user probe must not read a failure as "owns nothing".

`v0_8_1_security_constraints` decides whether to DELETE or merely DISABLE the
transitional legacy system user, based on whether that user still owns items.
The probe caught `Exception` and defaulted to `has_items = False`, which is the
destructive direction: `auth.users` references cascade, so deleting the row
takes the user's entire collection with it.

The migration's own `check_user_auth_method` guard does not save the data --
it counts rows in `auth.users`, and the deleted row is no longer there.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any
from unittest import mock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

MODULE = "migrations.versions.v0_8_1_security_constraints"


def _is_ownership_probe(statement: Any) -> bool:
    """Whether a statement is the legacy-user ownership probe.

    @param statement: The statement about to run.
    @returns: True for the `SELECT 1 ... owner_id ... LIMIT 1` probe.
    """
    text = str(statement)
    return "owner_id" in text and "LIMIT 1" in text and text.lstrip().upper().startswith("SELECT")


@pytest.fixture
def ops(app: Any) -> Any:
    """An Alembic Operations bound to the test database.

    A real Connection is used, not a proxy, because the migration calls
    `sa.inspect(bind)` and SQLAlchemy needs to recognise the object.
    `Operations.context()` is required rather than a bare constructor, or
    `get_bind()` has no proxy to delegate to.

    @param app: The Flask application fixture.
    @returns: An Operations instance, with its connection exposed.
    """
    from app.db import db

    connection = db.engine.connect()
    ctx = MigrationContext.configure(connection)
    with Operations.context(ctx) as operations:
        yield operations
    connection.close()


def test_probe_failure_aborts_instead_of_deleting(ops: Any) -> None:
    """A failing ownership probe must raise rather than silently disable the account.

    @param ops: The bound Alembic Operations.
    @returns: Nothing; the guard not firing fails the test.
    """
    migration = import_module(MODULE)
    real_execute = ops.get_bind().execute
    seen: list[str] = []

    def fake_execute(statement: Any, *args: Any, **kwargs: Any) -> Any:
        """Record, then fail the ownership probe only.

        @param statement: The statement about to run.
        @param args: Extra positional arguments.
        @param kwargs: Extra keyword arguments.
        @returns: The real result for any other statement.
        @raises RuntimeError: Always, for the ownership probe.
        """
        seen.append(str(statement))
        if _is_ownership_probe(statement):
            raise RuntimeError("simulated connection loss")
        return real_execute(statement, *args, **kwargs)

    with mock.patch.object(ops.get_bind(), "execute", side_effect=fake_execute):
        with pytest.raises(RuntimeError, match="refuses to decide"):
            migration.upgrade()

    assert any(_is_ownership_probe(s) for s in seen), "the probe never ran, so nothing was proven"


def test_probe_failure_mutates_nothing(ops: Any) -> None:
    """The abort must happen before any DELETE or UPDATE is issued.

    Raising is only safe if nothing ran first, which is what makes this the
    assertion that matters.

    @param ops: The bound Alembic Operations.
    @returns: Nothing; any mutation before the abort fails the test.
    """
    migration = import_module(MODULE)
    real_execute = ops.get_bind().execute
    statements: list[str] = []

    def fake_execute(statement: Any, *args: Any, **kwargs: Any) -> Any:
        """Record every statement, failing the ownership probe only.

        @param statement: The statement about to run.
        @param args: Extra positional arguments.
        @param kwargs: Extra keyword arguments.
        @returns: The real result for any other statement.
        @raises RuntimeError: Always, for the ownership probe.
        """
        statements.append(str(statement))
        if _is_ownership_probe(statement):
            raise RuntimeError("simulated connection loss")
        return real_execute(statement, *args, **kwargs)

    with mock.patch.object(ops.get_bind(), "execute", side_effect=fake_execute):
        with pytest.raises(RuntimeError, match="refuses to decide"):
            migration.upgrade()

    destructive = [s for s in statements if "DELETE" in s.upper() or "UPDATE" in s.upper()]
    assert not destructive, f"the migration mutated auth.users before failing: {destructive}"


def test_probe_is_not_swallowed_anywhere_in_the_module() -> None:
    """No bare `except Exception` may remain in the migration.

    A source-level guard as well as the behavioural ones, because the SQLite
    branch cannot be reached by these tests -- the test database has no legacy
    user, and no `inventory.items` table to be unreadable.

    @returns: Nothing; a reintroduced swallow fails the test.
    """
    import inspect

    source = inspect.getsource(import_module(MODULE))
    assert "except Exception:" not in source, "the legacy-user probe can swallow again"
    assert "has_items = False" not in source, "the destructive default is back"


def test_probe_error_names_the_remedy_and_promises_no_change() -> None:
    """The abort must tell the operator what to do, and that nothing was lost.

    @returns: Nothing; missing guidance fails the test.
    """
    import inspect

    source = inspect.getsource(import_module(MODULE))
    assert "nothing has been changed" in source, "the error must state that no data was touched"
    assert "inventory.items" in source, "the error must name the relation that must be readable"
