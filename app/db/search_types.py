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
"""Portable SQLAlchemy type for Full-Text Search vectors.

Compiles to ``TSVECTOR`` on PostgreSQL and ``TEXT`` on all other dialects.
"""

from sqlalchemy import Text
from sqlalchemy.ext.compiler import compiles


class SearchVector(Text):
    """A dialect-aware column type for search vectors.

    - PostgreSQL: stored as ``TSVECTOR``
    - All other dialects (SQLite, etc.): stored as ``TEXT``
    """


@compiles(SearchVector, "postgresql")
def compile_search_vector_pg(element, compiler, **kw) -> str:  # noqa: ARG001
    """Render a generated column as a PostgreSQL TSVECTOR.

    Registered with SQLAlchemy's ``@compiles`` so the same model definition works on
    PostgreSQL and SQLite. The element is ignored: the database maintains the value,
    not Python."""
    return "TSVECTOR"


@compiles(SearchVector)
def compile_search_vector_default(element, compiler, **kw) -> str:  # noqa: ARG001
    """Render a generated column as plain text outside PostgreSQL.

    SQLite has no TSVECTOR type, so the column degrades to the underlying text and
    the ILIKE fallback search path is used instead."""
    return str(compiler.visit_TEXT(element, **kw))
