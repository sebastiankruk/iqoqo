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

"""Guard the schema allowlist that Alembic autogenerate filters on.

`migrations/env.py:include_object` keeps autogenerate from proposing changes to
tables outside the schemas iqoqo manages. The list is a literal, and this test
exists because a literal drifts silently: a migration that placed tables in a
schema missing from that list would leave them **invisible to autogenerate** --
no error, no warning, just a missing migration in a later release.

Deriving the list from `db.metadata` was considered and rejected (see
openspec/changes/moderate-findings-sweep/tasks.md item 1.6). It could not have
worked in any case: all 44 tables in `db.metadata` have `schema=None`, because the
schema separation is expressed only in the migrations. So the literal stays and
this test guards it against drift.

`env.py` cannot be imported here -- it dereferences `alembic.context.config` at
module scope, which only exists while a migration run is in progress. Its AST is
parsed instead and just `include_object` is compiled out of it, so the real
filter is exercised without needing an Alembic context.
"""

import ast
from pathlib import Path

import pytest

ENV_PY = Path(__file__).resolve().parents[1] / "migrations" / "env.py"

# Kept in sync with migrations/env.py by test_allowlist_has_not_drifted.
EXPECTED_SCHEMAS = {"public", "catalog", "inventory", "auth", "social", "config"}


def _env_tree() -> ast.Module:
    """Parse migrations/env.py.

    @returns: Its abstract syntax tree.
    """
    return ast.parse(ENV_PY.read_text(encoding="utf-8"))


def _include_object_node() -> ast.FunctionDef:
    """Locate the `include_object` definition in migrations/env.py.

    @returns: Its syntax node.
    """
    for node in ast.walk(_env_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == "include_object":
            return node
    raise AssertionError("migrations/env.py no longer defines include_object")


def _allowlisted_schemas() -> set[str]:
    """Read the allowlist the real filter applies.

    Taken from the assignment inside `include_object` rather than duplicated
    here, so the test cannot pass by asserting against its own copy while the
    real filter disagrees.

    @returns: The schema names in the allowlist.
    """
    for node in ast.walk(_include_object_node()):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "allowed_schemas" for target in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError("include_object no longer assigns a literal `allowed_schemas`")


@pytest.fixture(scope="module")
def include_object():
    """Compile `include_object` out of migrations/env.py.

    @returns: The real filter, callable.
    """
    node = _include_object_node()
    module = ast.Module(body=[node], type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(ast.fix_missing_locations(module), str(ENV_PY), "exec"), namespace)  # noqa: S102
    return namespace["include_object"]


def _schemas_referenced_by_migrations() -> set[str]:
    """Collect every schema name the migrations place tables in.

    The schema separation lives **only in the migrations**, not in the ORM: all
    44 tables in `db.metadata` have `schema=None`, and the baseline assigns
    schemas through local aliases (`s_soc = "social"`), which is why a naive
    search for `schema=` misses most of them. So the set is gathered from the
    three places a schema name can appear:

    - `schema=<literal>` keyword arguments
    - assignments to the `s_*` aliases the baseline and later revisions use
    - `CREATE SCHEMA IF NOT EXISTS <name>` inside executed SQL

    @returns: The schema names referenced by migrations/versions/*.py.
    """
    import ast
    import re

    versions = ENV_PY.parent / "versions"
    found: set[str] = set()
    create_schema = re.compile(r"CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)", re.IGNORECASE)
    # `CREATE SCHEMA IF NOT EXISTS {schema}` interpolates a variable, so the
    # optional group is not always consumed and the capture can land on a SQL
    # keyword. Those are not schema names.
    sql_words = {"if", "not", "exists", "schema", "create", "public"}

    def literal(node: ast.expr) -> str | None:
        """Return the string a node resolves to.

        The schema aliases are ternaries that yield None on SQLite --
        `"social" if is_pg else None` -- so the PostgreSQL branch is taken as the
        intended schema.

        @param node: The value expression to read.
        @returns: The string value, or None when there is not exactly one.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.IfExp):
            return literal(node.body)
        return None

    for path in sorted(versions.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        found.update(name for name in create_schema.findall(source) if name.lower() not in sql_words)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.keyword) and node.arg == "schema":
                value = literal(node.value)
                if value:
                    found.add(value)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and (re.fullmatch(r"s_[a-z0-9_]+", target.id) or target.id.endswith("_schema")):
                        value = literal(node.value)
                        if value:
                            found.add(value)
    return found


def test_allowlist_covers_every_schema_the_migrations_use() -> None:
    """Every schema the migrations place tables in must be allowlisted.

    This is the real drift risk, and it is not the one the task described. A
    migration that created tables in a seventh schema would place them outside
    the allowlist, so autogenerate would filter those tables out and never
    propose the follow-up migration for them -- a silent omission rather than an
    error.

    Note this cannot be checked against the models: all 44 tables in
    `db.metadata` have `schema=None`, because the schema separation is expressed
    only in the migrations.

    @returns: Nothing; a missing schema fails the test.
    """
    referenced = _schemas_referenced_by_migrations()
    allowlisted = _allowlisted_schemas()

    missing = referenced - allowlisted
    assert not missing, (
        f"migrations place tables in schemas that autogenerate cannot see: {sorted(missing)}. "
        "Add them to the allowlist in migrations/env.py, or tables in those schemas will "
        f"silently never appear in a generated migration. Referenced: {sorted(referenced)}"
    )
    assert referenced, "no schemas found in the migrations; the extraction is broken, not the allowlist"


def test_allowlist_still_carries_public() -> None:
    """`public` holds Alembic's own version table and appears in no model.

    @returns: Nothing; a missing public entry fails the test.
    """
    allowlisted = _allowlisted_schemas()

    assert "public" in allowlisted, "alembic_version lives in public and must stay allowlisted"
    # Every non-public schema the migrations use must be listed, so a schema that
    # is dropped everywhere cannot quietly linger in the filter.
    referenced = _schemas_referenced_by_migrations() - {"public"}
    assert referenced <= allowlisted, f"migrations use schemas the allowlist omits: {sorted(referenced - allowlisted)}"


def test_allowlist_has_not_drifted() -> None:
    """The allowlist must match the set this test was audited against.

    A renamed or retired schema should be noticed rather than lingering, and any
    change here is a deliberate decision that has to touch both files.

    @returns: Nothing; an unexpected schema fails the test.
    """
    allowlisted = _allowlisted_schemas()

    assert allowlisted == EXPECTED_SCHEMAS, (
        f"the allowlist drifted from the audited set: {sorted(allowlisted)}. "
        "Update EXPECTED_SCHEMAS here and the comment in migrations/env.py together."
    )


@pytest.mark.parametrize("schema", sorted(EXPECTED_SCHEMAS))
def test_allowlisted_table_passes_the_filter(include_object, schema: str) -> None:
    """A table in an allowlisted schema must survive the real filter.

    @param include_object: The compiled filter under test.
    @param schema: An allowlisted schema name.
    @returns: Nothing; a filtered-out table fails the test.
    """
    table = type("Table", (), {"schema": schema})()
    assert include_object(table, "anything", "table", True, None) is True


def test_table_in_an_unknown_schema_is_filtered_out(include_object) -> None:
    """A table outside the allowlist must be filtered out.

    The control for the tests above: without it, a filter that returned True for
    everything would pass them all.

    @param include_object: The compiled filter under test.
    @returns: Nothing; an accepted unknown table fails the test.
    """
    table = type("Table", (), {"schema": "some_other_app"})()
    assert include_object(table, "anything", "table", True, None) is False


def test_non_table_objects_are_not_filtered(include_object) -> None:
    """Columns and indexes carry no schema and must pass untouched.

    Filtering them would strip every column and index from every generated
    migration.

    @param include_object: The compiled filter under test.
    @returns: Nothing; a filtered-out non-table fails the test.
    """
    column = type("Column", (), {"schema": None})()

    assert include_object(column, "title", "column", True, None) is True
    assert include_object(column, "ix_items_title", "index", True, None) is True
