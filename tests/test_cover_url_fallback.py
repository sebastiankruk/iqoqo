"""Tests for cover_url fallback logic in API responses."""

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

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def test_data(app):
    with app.app_context():
        user = User(email="test@iqoqo.local", display_name="Test User")
        db.session.add(user)
        db.session.commit()

        work = Work(title="Fallback Test", meta={"authors": ["Author X"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        # Manifestation with NO cover_url in column, but HAS it in meta
        m1 = Manifestation(
            expression_id=expr.id,
            isbn13="1111111111111",
            cover_url=None,
            meta={"cover_url": "http://external.com/cover1.jpg", "cover_status": "pending"},
        )

        # Manifestation with cover_url in BOTH column and meta (column should win)
        m2 = Manifestation(
            expression_id=expr.id,
            isbn13="2222222222222",
            cover_url="/static/covers/local2.jpg",
            meta={"cover_url": "http://external.com/ignored.jpg"},
        )

        db.session.add_all([m1, m2])
        db.session.flush()

        item1 = Item(manifestation_id=m1.id, owner_id=user.id)
        item2 = Item(manifestation_id=m2.id, owner_id=user.id)
        db.session.add_all([item1, item2])
        db.session.commit()

        token = generate_internal_jwt(user)
        return {"token": token, "manif1_id": m1.id, "manif2_id": m2.id, "item1_id": item1.id, "item2_id": item2.id}


def test_items_list_cover_url_fallback(client, test_data):
    """GET /api/items should fallback to meta['cover_url'] if column is null."""
    headers = {"Authorization": f"Bearer {test_data['token']}"}
    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    items = response.json["data"]

    # Sort items by ISBN for predictable checking
    items.sort(key=lambda x: x["isbn"])

    # Item 1: Fallback case
    assert items[0]["isbn"] == "1111111111111"
    assert items[0]["cover_url"] == "http://external.com/cover1.jpg"

    # Item 2: Preferred case
    assert items[1]["isbn"] == "2222222222222"
    assert items[1]["cover_url"] == "/static/covers/local2.jpg"


def test_item_detail_cover_url_fallback(client, test_data):
    """GET /api/items/<id> should fallback to meta['cover_url'] if column is null."""
    headers = {"Authorization": f"Bearer {test_data['token']}"}

    # Test Item 1 (Fallback)
    response = client.get(f"/api/items/{test_data['item1_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["cover_url"] == "http://external.com/cover1.jpg"

    # Test Item 2 (Preferred)
    response = client.get(f"/api/items/{test_data['item2_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["cover_url"] == "/static/covers/local2.jpg"


def test_recent_manifestations_cover_url_fallback(client, test_data):
    """GET /api/manifestations/recent should fallback to meta['cover_url']."""
    response = client.get("/api/manifestations/recent")
    assert response.status_code == 200
    manifs = response.json["data"]

    # Sort by ID for matching
    m_dict = {m["id"]: m for m in manifs}

    assert m_dict[test_data["manif1_id"]]["cover_url"] == "http://external.com/cover1.jpg"
    assert m_dict[test_data["manif2_id"]]["cover_url"] == "/static/covers/local2.jpg"
