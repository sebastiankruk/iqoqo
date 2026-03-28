"""Integration tests for PostgreSQL Full-Text Search (FTS) triggers and computed columns."""

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

import os
import time

import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from app import create_app
from app.db import db
from app.db.models import Expression, Manifestation, Work


@pytest.fixture(scope="module")
def postgres_db():
    """Spin up a fresh PostgreSQL container for the duration of the module."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        os.environ["DATABASE_URL"] = postgres.get_connection_url()
        os.environ["ENABLE_FTS_TESTS"] = "true"

        app = create_app()
        with app.app_context():
            # Create all tables (this includes the Computed columns and GIN indices)
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()


def test_fts_works_computation(postgres_db):
    """Verify that inserting a Work correctly populates fts_simple."""
    with postgres_db.app_context():
        # 1. Insert a Work
        work = Work(
            title="The Hobbit",
            meta={"authors": "J.R.R. Tolkien"}
        )
        db.session.add(work)
        db.session.commit()

        # 2. Query fts_simple directly using raw SQL to be sure
        result = db.session.execute(
            text("SELECT fts_simple FROM works WHERE id = :id"),
            {"id": work.id}
        ).fetchone()

        assert result is not None
        fts_val = result[0]
        # 'hobbit':1 'j.r.r.':2 'tolkien':3 (simplified version)
        assert "hobbit" in fts_val.lower()
        assert "tolkien" in fts_val.lower()

        # 3. Test search via tsquery
        search_results = Work.query.filter(
            text("fts_simple @@ to_tsquery('simple', 'hobbit & tolkien')")
        ).all()
        assert len(search_results) == 1
        assert search_results[0].title == "The Hobbit"


def test_fts_manifestations_computation(postgres_db):
    """Verify that inserting a Manifestation correctly populates fts_simple."""
    with postgres_db.app_context():
        # 1. Setup required Work and Expression
        work = Work(title="Foundations of Geopolitics")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, language="en")
        db.session.add(expr)
        db.session.flush()

        # 2. Insert Manifestation
        manifestation = Manifestation(
            expression_id=expr.id,
            isbn13="9780000000001",
            meta={
                "publisher": "Arktos",
                "alt_title": "The Fourth Political Theory"
            }
        )
        db.session.add(manifestation)
        db.session.commit()

        # 3. Query fts_simple
        result = db.session.execute(
            text("SELECT fts_simple FROM manifestations WHERE id = :id"),
            {"id": manifestation.id}
        ).fetchone()

        assert result is not None
        fts_val = result[0]
        assert "9780000000001" in fts_val
        assert "arktos" in fts_val.lower()
        assert "fourth" in fts_val.lower()

        # 4. Search
        search_results = Manifestation.query.filter(
            text("fts_simple @@ to_tsquery('simple', 'arktos & fourth')")
        ).all()
        assert len(search_results) == 1
        assert search_results[0].isbn13 == "9780000000001"
