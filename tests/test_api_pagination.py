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
