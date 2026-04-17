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
from sqlalchemy import create_mock_engine
from sqlalchemy.schema import CreateTable

from app.core.search_service import SearchService
from app.db.models import Expression, Item, Manifestation, User, Work, db


def test_search_vector_compiles_to_text_on_sqlite():
    """Verify SearchVector renders as TEXT for SQLite (used in tests)."""
    # Create a dummy sqlite engine
    engine = db.create_engine("sqlite://")

    # Generate CREATE TABLE statement
    ddl = str(CreateTable(Work.__table__).compile(engine))

    # On SQLite, fts_simple should be TEXT (not TSVECTOR)
    assert "fts_simple TEXT" in ddl
    assert "TSVECTOR" not in ddl


def test_search_service_fallback_on_sqlite(app):
    """Ensure SearchService falls back to ILIKE on SQLite and works."""

    with app.app_context():
        work = Work(title="The Portable Hobbit", meta={"authors": ["Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(manif)
        db.session.commit()

        # Test manifestation search
        total, ids = SearchService.search_manifestations("Portable", 10, 0)
        assert total == 1
        assert ids[0] == manif.id

        # Test no results
        total, ids = SearchService.search_manifestations("DoesNotExist", 10, 0)
        assert total == 0
        assert len(ids) == 0


def test_search_service_items_fallback_on_sqlite(app, normal_user_headers):
    """Ensure SearchService item search falls back to ILIKE on SQLite."""

    with app.app_context():
        # Get user from normal_user_headers
        user = User.query.first()

        work = Work(title="Searchable Book", meta={"authors": ["AuthorX"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9999999999999")
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, status="available")
        db.session.add(item)
        db.session.commit()

        total, results = SearchService.search_items("Searchable", user.id, 10, 0)
        assert total == 1
        assert results[0]["item_id"] == item.id
        assert results[0]["title"] == "Searchable Book"
