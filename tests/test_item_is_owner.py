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

from app.api.auth import generate_internal_jwt
from app.db.models import Item, Manifestation, User, Work, db


@pytest.fixture
def test_data(app):
    with app.app_context():
        user1 = User(display_name="user1", email="user1@example.com")
        user2 = User(display_name="user2", email="user2@example.com")
        db.session.add_all([user1, user2])
        db.session.commit()

        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()

        from app.db.models import Expression

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(manif)
        db.session.flush()

        item1 = Item(manifestation_id=manif.id, owner_id=user1.id, status="available")
        db.session.add(item1)
        db.session.commit()

        # Return IDs to avoid DetachedInstanceError
        return user1.id, user2.id, item1.id


def test_get_item_detail_is_owner(app, client, test_data):
    """Test that is_owner is true when the requesting user owns the item."""
    user1_id, _, item1_id = test_data

    with app.app_context():
        user1 = db.session.get(User, user1_id)
        token = generate_internal_jwt(user1)

    resp = client.get(f"/api/items/{item1_id}", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["is_owner"] is True
    assert data["owner_id"] == str(user1_id)


def test_get_item_detail_not_owner(app, client, test_data):
    """Test that is_owner is false when someone else owns the item."""
    _, user2_id, item1_id = test_data

    with app.app_context():
        user2 = db.session.get(User, user2_id)
        token = generate_internal_jwt(user2)

    resp = client.get(f"/api/items/{item1_id}", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["is_owner"] is False
    assert data["owner_id"] == "Unavailable"


def test_get_item_detail_anonymous(client, test_data):
    """Test that is_owner is false for anonymous users."""
    _, _, item1_id = test_data

    resp = client.get(f"/api/items/{item1_id}")

    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["is_owner"] is False
    assert data["owner_id"] == "Unavailable"
