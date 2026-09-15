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

from app.db import db
from app.db.models import Expression, Item, Manifestation, User, Work


def test_works_shelf_pagination(client, normal_user_headers, app):
    """Test pagination for /works/shelf endpoint."""
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()
        # Seed multiple works
        for i in range(5):
            work = Work(title=f"Work {i}")
            db.session.add(work)
            db.session.commit()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.commit()

            man = Manifestation(expression_id=expr.id, meta={"title": f"Man {i}", "format": "book"})
            db.session.add(man)
            db.session.commit()

            item = Item(manifestation_id=man.id, owner_id=user.id)
            db.session.add(item)
            db.session.commit()

    # Request first page with limit 2
    res1 = client.get("/api/works/shelf?limit=2&offset=0", headers=normal_user_headers)
    assert res1.status_code == 200
    data1 = res1.json
    assert data1["success"] is True
    assert len(data1["data"]) == 2
    assert data1["pagination"]["total"] >= 5
    assert data1["pagination"]["limit"] == 2
    assert data1["pagination"]["offset"] == 0
    assert data1["pagination"]["has_more"] is True

    # Request second page with limit 2
    res2 = client.get("/api/works/shelf?limit=2&offset=2", headers=normal_user_headers)
    assert res2.status_code == 200
    data2 = res2.json
    assert len(data2["data"]) == 2
    assert data2["pagination"]["offset"] == 2
    assert data1["data"][0]["work_id"] != data2["data"][0]["work_id"]


def test_expressions_shelf_pagination(client, normal_user_headers, app):
    """Test pagination for /expressions/shelf endpoint."""
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()
        # Seed multiple expressions for a single work to verify expression grouping
        work = Work(title="Expression Group Work")
        db.session.add(work)
        db.session.commit()

        for i in range(5):
            expr = Expression(work_id=work.id, content_type="text", language=f"Lang {i}")
            db.session.add(expr)
            db.session.commit()

            man = Manifestation(expression_id=expr.id, meta={"title": f"Man Expr {i}", "format": "book"})
            db.session.add(man)
            db.session.commit()

            item = Item(manifestation_id=man.id, owner_id=user.id)
            db.session.add(item)
            db.session.commit()

    # Request first page with limit 2
    res1 = client.get("/api/expressions/shelf?limit=2&offset=0", headers=normal_user_headers)
    assert res1.status_code == 200
    data1 = res1.json
    assert data1["success"] is True
    assert len(data1["data"]) == 2
    assert data1["pagination"]["total"] >= 5
    assert data1["pagination"]["limit"] == 2
    assert data1["pagination"]["offset"] == 0
    assert data1["pagination"]["has_more"] is True

    # Request second page with limit 2
    res2 = client.get("/api/expressions/shelf?limit=2&offset=2", headers=normal_user_headers)
    assert res2.status_code == 200
    data2 = res2.json
    assert len(data2["data"]) == 2
    assert data2["pagination"]["offset"] == 2
    assert data1["data"][0]["expression_id"] != data2["data"][0]["expression_id"]


def test_items_pagination(client, normal_user_headers, app):
    """Test SQL-level pagination for /api/items endpoint."""
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()
        for i in range(6):
            work = Work(title=f"Paged Item Work {i}")
            db.session.add(work)
            db.session.commit()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.commit()

            man = Manifestation(expression_id=expr.id, meta={"title": f"Paged Man {i}", "format": "book"})
            db.session.add(man)
            db.session.commit()

            item = Item(manifestation_id=man.id, owner_id=user.id, status="available")
            db.session.add(item)
            db.session.commit()

    # Request first page with limit 3, page 1
    res1 = client.get("/api/items?limit=3&page=1", headers=normal_user_headers)
    assert res1.status_code == 200
    data1 = res1.json
    assert data1["success"] is True
    assert len(data1["data"]) == 3
    assert data1["meta"]["limit"] == 3
    assert data1["meta"]["page"] == 1
    assert data1["meta"]["total"] >= 6
    assert data1["pagination"]["has_more"] is True

    # Request second page with limit 3, page 2
    res2 = client.get("/api/items?limit=3&page=2", headers=normal_user_headers)
    assert res2.status_code == 200
    data2 = res2.json
    assert len(data2["data"]) == 3
    assert data2["meta"]["page"] == 2
    ids1 = {it["id"] for it in data1["data"]}
    ids2 = {it["id"] for it in data2["data"]}
    assert ids1.isdisjoint(ids2)


def test_fresh_arrivals_pagination_deduplication(app):
    """Test fetch_global_fresh_arrivals database-level deduplication and limits."""
    from app.api.public import fetch_global_fresh_arrivals

    with app.app_context():
        # Create a public user
        user = User.query.filter_by(public_username="public_fresh_user").first()
        if not user:
            user = User(email="fresh_public@iqoqo.local", public_username="public_fresh_user", visibility="public")
            db.session.add(user)
            db.session.commit()

        # Create one work with two items (via two manifestations)
        work = Work(title="Deduplicated Work")
        db.session.add(work)
        db.session.commit()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.commit()

        m1 = Manifestation(expression_id=expr.id, meta={"title": "M1"})
        m2 = Manifestation(expression_id=expr.id, meta={"title": "M2"})
        db.session.add_all([m1, m2])
        db.session.commit()

        i1 = Item(manifestation_id=m1.id, owner_id=user.id, is_hidden=False, status="available")
        i2 = Item(manifestation_id=m2.id, owner_id=user.id, is_hidden=False, status="available")
        i3 = Item(manifestation_id=m1.id, owner_id=user.id, is_hidden=False, status="available")
        db.session.add_all([i1, i2, i3])
        db.session.commit()

        # Fetch works level with limit 10
        work_items = fetch_global_fresh_arrivals(limit=10, level="works")
        work_ids = [it.manifestation.expression.work_id for it in work_items if it.manifestation and it.manifestation.expression]
        # Should have no duplicate work IDs
        assert len(work_ids) == len(set(work_ids))

        # Fetch expressions level
        expr_items = fetch_global_fresh_arrivals(limit=10, level="expressions")
        expr_ids = [it.manifestation.expression_id for it in expr_items if it.manifestation]
        assert len(expr_ids) == len(set(expr_ids))

        # Fetch manifestations level
        manif_items = fetch_global_fresh_arrivals(limit=10, level="manifestations")
        manif_ids = [it.manifestation_id for it in manif_items if it.manifestation_id]
        assert len(manif_ids) == len(set(manif_ids))
