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
"""Extended tests for the public API endpoints."""

import json
import pytest
from app.db.models import User, Item, Manifestation, Expression, Work, SharedCollection, db

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            email="extended@iqoqo.local",
            public_username="extuser",
            visibility="public"
        )
        db.session.add(user)
        db.session.commit()
        return user.public_username

def test_pagination(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Pagination Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()
        
        for i in range(15):
            item = Item(owner_id=user.id, manifestation_id=mani.id, status="read")
            db.session.add(item)
        db.session.commit()

    # Page 1
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=1")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 10
    assert data["data"]["total"] == 15
    assert data["data"]["pages"] == 2

    # Page 2
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=2")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 5

def test_shared_collection_with_status_filter(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Shared Filter Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()
        
        # 2 read, 1 wishlist
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="wish_list"))
        
        collection = SharedCollection(
            user_id=user.id,
            name="My Read Books",
            filters={"status": "read"}
        )
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 2
    for item in data["data"]["items"]:
        assert item["status"] == "read"

def test_check_inventory_missing_query(client, test_user):
    response = client.post(f"/api/public/u/{test_user}/check", json={})
    assert response.status_code == 400
    assert "required" in json.loads(response.data)["error"]
