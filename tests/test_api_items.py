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
