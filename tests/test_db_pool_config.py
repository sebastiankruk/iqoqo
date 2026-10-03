"""Tests for database pool configuration and session teardown."""

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

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

from app import create_app

CONFIG_PY = Path(__file__).resolve().parents[1] / "app" / "config.py"


def load_config(env: dict[str, str]) -> ModuleType:
    """Execute `app/config.py` from scratch with a controlled environment.

    `Config.SQLALCHEMY_ENGINE_OPTIONS` is computed in the class body, so it is
    read from the environment once, when the module is imported. Setting
    `os.environ` and calling `create_app()` cannot re-trigger it, which is why
    the previous version of this file never actually exercised the parsing: it
    declared a subclass holding a literal dict and then asserted the literal.

    The module is loaded under a fresh name from its own path rather than
    reloaded in place, so a test can never leave `app.config` -- which every
    other test imports -- pointing at values from a patched environment.

    @param env: The environment variables `app/config.py` should see.
    @returns: The freshly executed module.
    """
    # A unique name each call, so two tests never share a module object and
    # sys.modules never accumulates throwaway entries for a long-lived process.
    name = f"iqoqo_config_under_test_{id(env):x}"
    spec = importlib.util.spec_from_file_location(name, CONFIG_PY)
    assert spec is not None and spec.loader is not None, f"could not load {CONFIG_PY}"
    module = importlib.util.module_from_spec(spec)
    try:
        with patch.dict(os.environ, env):
            spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def engine_options(env: dict[str, str]) -> dict:
    """Return the engine options `app/config.py` derives from an environment.

    @param env: The environment variables to configure.
    @returns: The `SQLALCHEMY_ENGINE_OPTIONS` dict, empty for non-PostgreSQL.
    """
    return load_config(env).Config.SQLALCHEMY_ENGINE_OPTIONS


PG = "postgresql://user:pass@localhost/db"


def test_sqlite_engine_has_no_pool_options():
    """SQLite must not receive PostgreSQL pool options.

    SQLite has no connection pool, so `pool_size` raises at engine creation.
    The test suite runs on SQLite, which makes this the difference between the
    suite working at all and every test erroring in setup.

    @returns: Nothing; any pool option fails the test.
    """
    with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///:memory:"}):
        app = create_app()
        engine_options_ = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})

    assert "pool_size" not in engine_options_
    assert "max_overflow" not in engine_options_


def test_postgres_pool_size_is_parsed_from_the_environment():
    """`SQLALCHEMY_POOL_SIZE` must actually reach the engine options.

    The previous test asserted `opts["pool_size"] == 7` against a dict literal it
    had just written into a local subclass, so it passed whether or not the
    environment was read at all. Setting a distinctive value also catches a
    regression that swapped the two variables.

    @returns: Nothing; a wrong or default value fails the test.
    """
    options = engine_options({"DATABASE_URL": PG, "SQLALCHEMY_POOL_SIZE": "7", "SQLALCHEMY_MAX_OVERFLOW": "13"})

    assert options["pool_size"] == 7
    assert options["max_overflow"] == 13


def test_postgres_pool_defaults_when_unset():
    """Unset pool variables must yield the documented defaults.

    @returns: Nothing; a wrong default fails the test.
    """
    options = engine_options({"DATABASE_URL": PG})

    assert options["pool_size"] == 5
    assert options["max_overflow"] == 10
    # These two are not configurable; they exist to reclaim connections dropped
    # by a restarting database and to fail fast on a stale socket.
    assert options["pool_recycle"] == 300
    assert options["pool_pre_ping"] is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("not-a-number", 5),
        ("", 5),
        ("  ", 5),
        ("3.5", 5),
        ("0", 0),
        ("-1", -1),
        (" 7 ", 7),
    ],
)
def test_unparseable_pool_size_falls_back_to_the_default(raw: str, expected: int):
    """`_get_int_env` must degrade to the default rather than crash the app.

    A malformed value in a deployment's `.env` should not stop the process from
    starting. `int()` raises `ValueError` for these inputs and the helper
    catches it; `int(" 7 ")` succeeds because Python tolerates surrounding
    whitespace.

    The `"0"` and `"-1"` rows document behaviour rather than endorse it: both are
    accepted and would be rejected by SQLAlchemy at engine creation. Validating
    the range is a separate concern from parsing it, and is not asserted here.

    @param raw: The literal environment value.
    @param expected: The `pool_size` that should result.
    @returns: Nothing; a wrong parse fails the test.
    """
    options = engine_options({"DATABASE_URL": PG, "SQLALCHEMY_POOL_SIZE": raw})

    assert options["pool_size"] == expected


@pytest.mark.parametrize(
    "uri",
    [
        "postgresql://user:pass@localhost/db",
        "postgresql+psycopg2://user:pass@localhost/db",
        "POSTGRES://user:pass@localhost/db",
        "postgres://user:pass@localhost/db",
    ],
)
def test_postgres_detection_is_scheme_and_case_insensitive(uri: str):
    """Every PostgreSQL URL spelling must receive pool options.

    Detection is a substring check on `"postgres"`, so the driver suffix and the
    scheme casing both have to keep working -- a deployment that writes
    `POSTGRESQL://` in its `.env` must not silently lose connection pooling.

    @param uri: The database URL spelling.
    @returns: Nothing; missing pool options fails the test.
    """
    options = engine_options({"DATABASE_URL": uri, "SQLALCHEMY_POOL_SIZE": "9"})

    assert options["pool_size"] == 9, f"{uri} was not recognised as PostgreSQL"


@pytest.mark.parametrize("uri", ["sqlite:///:memory:", "sqlite:////tmp/iqoqo.db"])
def test_sqlite_urls_receive_no_pool_options(uri: str):
    """A non-PostgreSQL URL must get an empty options dict.

    @param uri: The database URL.
    @returns: Nothing; any pool option fails the test.
    """
    assert engine_options({"DATABASE_URL": uri, "SQLALCHEMY_POOL_SIZE": "9"}) == {}


def test_pool_options_are_not_derived_for_an_absent_database_url():
    """No `DATABASE_URL` must not be mistaken for PostgreSQL.

    @returns: Nothing; pool options without a URL fails the test.
    """
    assert engine_options({}) == {}


def test_session_teardown_registered(app):
    """Verify that the shutdown_session handler is registered in the app."""
    # In Flask 3.x, app.teardown_appcontext_funcs is a list of functions
    handler_names = [f.__name__ for f in app.teardown_appcontext_funcs]
    assert "shutdown_session" in handler_names


def test_session_remove_called_on_teardown(app):
    """Verify that db.session.remove() is called when the app context is torn down."""
    with patch("app.db.db.session.remove") as mock_remove:
        # Pushing and popping a context should trigger teardown
        with app.app_context():
            pass
        assert mock_remove.called
