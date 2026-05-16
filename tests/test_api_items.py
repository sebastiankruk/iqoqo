# tests/test_api_items.py
"""Tests for the /api/items endpoint filtering."""

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

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def items_with_different_categories(app):
    """Seed the database with items across different categories."""
    with app.app_context():
        user = User(email="filter_test@iqoqo.local", display_name="Filter Tester")
        db.session.add(user)
        db.session.flush()

        # 1. Text category
        w1 = Work(title="Book One")
        db.session.add(w1)
        db.session.flush()
        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
        db.session.add(e1)
        db.session.flush()
        m1 = Manifestation(expression_id=e1.id, meta={"format": MediaFormat.BOOK})
        db.session.add(m1)
        db.session.flush()
        i1 = Item(manifestation_id=m1.id, owner_id=user.id, status="available")
        db.session.add(i1)

        # 2. Music category
        w2 = Work(title="Album One")
        db.session.add(w2)
        db.session.flush()
        e2 = Expression(work_id=w2.id, content_type=MediaCategory.MUSIC)
        db.session.add(e2)
        db.session.flush()
        m2 = Manifestation(expression_id=e2.id, meta={"format": MediaFormat.CD})
        db.session.add(m2)
        db.session.flush()
        i2 = Item(manifestation_id=m2.id, owner_id=user.id, status="available")
        db.session.add(i2)

        # 3. Board Game category with Cards format
        w3 = Work(title="Game One")
        db.session.add(w3)
        db.session.flush()
        e3 = Expression(work_id=w3.id, content_type=MediaCategory.BOARD_GAME)
        db.session.add(e3)
        db.session.flush()
        m31 = Manifestation(expression_id=e3.id, meta={"format": MediaFormat.BOARD_GAME})
        db.session.add(m31)
        db.session.flush()
        i31 = Item(manifestation_id=m31.id, owner_id=user.id, status="available")
        db.session.add(i31)

        m32 = Manifestation(expression_id=e3.id, meta={"format": MediaFormat.CARDS})
        db.session.add(m32)
        db.session.flush()
        i32 = Item(manifestation_id=m32.id, owner_id=user.id, status="available")
        db.session.add(i32)

        db.session.commit()
        return user.id


def test_get_items_filtered_by_category(client, items_with_different_categories, app):
    """Test GET /api/items?category=..."""
    user_id = items_with_different_categories
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter by text
    response = client.get("/api/items?category=text", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Book One"

    # Filter by music
    response = client.get("/api/items?category=music", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Album One"


def test_get_items_filtered_by_format(client, items_with_different_categories, app):
    """Test GET /api/items?format=..."""
    user_id = items_with_different_categories
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter by cards (should only get the card game)
    response = client.get("/api/items?category=board_game&format=cards", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Game One"


def test_get_items_search_with_filters(client, items_with_different_categories, app):
    """Test that search query correctly respects category/format filters."""
    user_id = items_with_different_categories
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Search for "One" in "music" category - should only find Album One
    response = client.get("/api/items?q=One&category=music", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Album One"

    # Search for "One" in "text" category - should only find Book One
    response = client.get("/api/items?q=One&category=text", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Book One"


@pytest.fixture
def items_for_quality_filters(app):
    """Seed items with different quality states (missing cover/ID)."""
    with app.app_context():
        from app.core.permissions import PermissionName
        from app.db.models import Permission, Role

        write_perm = Permission.query.filter_by(name=PermissionName.WRITE_ITEM).first()
        if not write_perm:
            write_perm = Permission(name=PermissionName.WRITE_ITEM)
            db.session.add(write_perm)
        user_role = Role(name="quality_tester")
        user_role.permissions.append(write_perm)
        db.session.add(user_role)
        db.session.flush()

        user = User(email="quality_test@iqoqo.local", display_name="Quality Tester")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # 1. Has both cover and ID
        w1 = Work(title="Perfect Item")
        db.session.add(w1)
        db.session.flush()
        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
        db.session.add(e1)
        db.session.flush()
        m1 = Manifestation(expression_id=e1.id, isbn13="9780000000001", cover_url="http://example.com/cover.jpg")
        db.session.add(m1)
        db.session.flush()
        i1 = Item(manifestation_id=m1.id, owner_id=user.id)
        db.session.add(i1)

        # 2. Missing cover (column) but has cover in meta
        w2 = Work(title="Meta Cover Item")
        db.session.add(w2)
        db.session.flush()
        e2 = Expression(work_id=w2.id, content_type=MediaCategory.TEXT)
        db.session.add(e2)
        db.session.flush()
        m2 = Manifestation(expression_id=e2.id, isbn13="9780000000002", meta={"cover_url": "http://example.com/meta.jpg"})
        db.session.add(m2)
        db.session.flush()
        i2 = Item(manifestation_id=m2.id, owner_id=user.id)
        db.session.add(i2)

        # 3. Missing cover entirely
        w3 = Work(title="No Cover Item")
        db.session.add(w3)
        db.session.flush()
        e3 = Expression(work_id=w3.id, content_type=MediaCategory.TEXT)
        db.session.add(e3)
        db.session.flush()
        m3 = Manifestation(expression_id=e3.id, isbn13="9780000000003")
        db.session.add(m3)
        db.session.flush()
        i3 = Item(manifestation_id=m3.id, owner_id=user.id)
        db.session.add(i3)

        # 4. Missing ISBN but has UPC
        w4 = Work(title="UPC Item")
        db.session.add(w4)
        db.session.flush()
        e4 = Expression(work_id=w4.id, content_type=MediaCategory.MOVIE)
        db.session.add(e4)
        db.session.flush()
        m4 = Manifestation(expression_id=e4.id, upc="123456789012", cover_url="http://example.com/v.jpg")
        db.session.add(m4)
        db.session.flush()
        i4 = Item(manifestation_id=m4.id, owner_id=user.id)
        db.session.add(i4)

        # 5. Missing ID entirely
        w5 = Work(title="No ID Item")
        db.session.add(w5)
        db.session.flush()
        e5 = Expression(work_id=w5.id, content_type=MediaCategory.TEXT)
        db.session.add(e5)
        db.session.flush()
        m5 = Manifestation(expression_id=e5.id, cover_url="http://example.com/c5.jpg")
        db.session.add(m5)
        db.session.flush()
        i5 = Item(manifestation_id=m5.id, owner_id=user.id)
        db.session.add(i5)

        db.session.commit()
        return user.id


def test_get_items_filtered_by_missing_cover(client, items_for_quality_filters, app):
    """Test GET /api/items?missing_cover=true"""
    user_id = items_for_quality_filters
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items?missing_cover=true", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    # Only "No Cover Item" should be returned.
    # "Perfect Item" has cover_url column.
    # "Meta Cover Item" has cover in meta.
    assert len(data) == 1
    assert data[0]["title"] == "No Cover Item"


def test_get_items_filtered_by_missing_id(client, items_for_quality_filters, app):
    """Test GET /api/items?missing_id=true"""
    user_id = items_for_quality_filters
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items?missing_id=true", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    # Only "No ID Item" should be returned.
    # "Perfect Item", "Meta Cover Item", "No Cover Item" have ISBNs.
    # "UPC Item" has UPC.
    assert len(data) == 1
    assert data[0]["title"] == "No ID Item"


def test_bulk_add_items_success(client, items_for_quality_filters, app):
    """Test POST /api/items/bulk creates multiple items from valid manifestation IDs."""
    user_id = items_for_quality_filters
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
        manifestations = db.session.query(Manifestation).limit(2).all()
        man_ids = [m.id for m in manifestations]

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "manifestation_ids": man_ids,
        "status": "want_to_read",
        "collection_status": "wishlist"
    }

    response = client.post("/api/items/bulk", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert len(data["data"]["item_ids"]) == 2
    assert sorted(data["data"]["manifestation_ids"]) == sorted(man_ids)

    with app.app_context():
        created_items = db.session.query(Item).filter(Item.id.in_(data["data"]["item_ids"])).all()
        assert len(created_items) == 2
        assert all(i.status == "want_to_read" for i in created_items)
        assert all(i.collection_status == "wishlist" for i in created_items)


def test_bulk_add_items_invalid_payload(client, items_for_quality_filters, app):
    """Test POST /api/items/bulk rejects empty array as dictated by strict Pydantic rules."""
    user_id = items_for_quality_filters
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/items/bulk", json={"status": "read"}, headers=headers)
    assert response.status_code == 400

    payload = {"manifestation_ids": []}
    response = client.post("/api/items/bulk", json=payload, headers=headers)
    assert response.status_code == 400


def test_bulk_add_items_not_found(client, items_for_quality_filters, app):
    """Test POST /api/items/bulk handles non-existent manifestation IDs gracefully."""
    user_id = items_for_quality_filters
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"manifestation_ids": [999998, 999999]}

    response = client.post("/api/items/bulk", json=payload, headers=headers)
    assert response.status_code == 404
    assert response.json["success"] is False
    assert "No valid manifestations found" in response.json["error"]
