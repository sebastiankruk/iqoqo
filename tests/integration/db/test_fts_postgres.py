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

import pytest
from sqlalchemy import text

from app import create_app
from app.db import db
from app.db.models import Expression, Manifestation, Work


@pytest.fixture(scope="module")
def postgres_db():
    """Use the PostgreSQL service from GitHub Actions workflow or skip if unavailable."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL not available – skipping PostgreSQL integration tests.")

    os.environ["DATABASE_URL"] = db_url
    os.environ["ENABLE_FTS_TESTS"] = "true"

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.execute(text("ALTER TABLE works DROP COLUMN IF EXISTS fts_simple CASCADE"))
        db.session.execute(
            text(
                "ALTER TABLE works ADD COLUMN fts_simple TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, (((COALESCE(title, ''::character varying))::text || ' '::text) || COALESCE((meta ->> 'authors'::text), ''::text)))) STORED"
            )
        )
        db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_works_fts ON works USING gin(fts_simple)"))

        db.session.execute(text("ALTER TABLE manifestations DROP COLUMN IF EXISTS fts_simple CASCADE"))
        db.session.execute(
            text(
                "ALTER TABLE manifestations ADD COLUMN fts_simple TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple'::regconfig, (((((COALESCE(isbn13, ''::character varying))::text || ' '::text) || COALESCE((meta ->> 'publisher'::text), ''::text)) || ' '::text) || COALESCE((meta ->> 'alt_title'::text), ''::text)))) STORED"
            )
        )
        db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_manifestations_fts ON manifestations USING gin(fts_simple)"))
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()


def test_fts_works_computation(postgres_db):
    """Verify that inserting a Work correctly populates fts_simple."""
    with postgres_db.app_context():
        # 1. Insert a Work
        work = Work(title="The Hobbit", meta={"authors": "J.R.R. Tolkien"})
        db.session.add(work)
        db.session.commit()

        # 2. Query fts_simple directly using raw SQL to be sure
        result = db.session.execute(text("SELECT fts_simple FROM works WHERE id = :id"), {"id": work.id}).fetchone()

        assert result is not None
        fts_val = result[0]
        # 'hobbit':1 'j.r.r.':2 'tolkien':3 (simplified version)
        assert "hobbit" in fts_val.lower()
        assert "tolkien" in fts_val.lower()

        # 3. Test search via tsquery
        search_results = Work.query.filter(text("fts_simple @@ to_tsquery('simple', 'hobbit & tolkien')")).all()
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
            expression_id=expr.id, isbn13="9780000000001", meta={"publisher": "Arktos", "alt_title": "The Fourth Political Theory"}
        )
        db.session.add(manifestation)
        db.session.commit()

        # 3. Query fts_simple
        result = db.session.execute(
            text("SELECT fts_simple FROM catalog.manifestations WHERE id = :id"), {"id": manifestation.id}
        ).fetchone()

        assert result is not None
        fts_val = result[0]
        assert "9780000000001" in fts_val
        assert "arktos" in fts_val.lower()
        assert "fourth" in fts_val.lower()

        # 4. Search
        search_results = Manifestation.query.filter(text("fts_simple @@ to_tsquery('simple', 'arktos & fourth')")).all()
        assert len(search_results) == 1
        assert search_results[0].isbn13 == "9780000000001"
