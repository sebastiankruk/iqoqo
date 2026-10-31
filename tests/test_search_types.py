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
"""Tests for dialect-aware SearchVector compilation in app/db/search_types.py."""

from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from app.db.search_types import SearchVector


def test_search_vector_compilation_postgresql():
    """SearchVector compiles to TSVECTOR on PostgreSQL dialect."""
    pg_dialect = postgresql.dialect()
    sv = SearchVector()
    compiled = sv.compile(dialect=pg_dialect)
    assert str(compiled) == "TSVECTOR"


def test_search_vector_compilation_sqlite():
    """SearchVector compiles to TEXT on SQLite dialect."""
    sqlite_dialect = sqlite.dialect()
    sv = SearchVector()
    compiled = sv.compile(dialect=sqlite_dialect)
    assert str(compiled) == "TEXT"


def test_search_vector_table_schema_compilation():
    """CreateTable generates dialect-appropriate column types for SearchVector."""
    metadata = MetaData()
    test_table = Table(
        "test_search_items",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("search_vector", SearchVector),
    )

    pg_sql = str(CreateTable(test_table).compile(dialect=postgresql.dialect()))
    assert "search_vector TSVECTOR" in pg_sql

    sqlite_sql = str(CreateTable(test_table).compile(dialect=sqlite.dialect()))
    assert "search_vector TEXT" in sqlite_sql
