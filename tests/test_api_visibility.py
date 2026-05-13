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
"""Tests for profile and item visibility API."""

import json
import pytest
from app.db.models import User, Item, Manifestation, Expression, Work, db
from app.api.auth import generate_internal_jwt

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email="visibility@iqoqo.local", display_name="Visibility User", visibility="private")
        db.session.add(user)
        db.session.commit()
        return user.id

@pytest.fixture
def auth_headers(app, test_user):
    with app.app_context():
        user = db.session.get(User, test_user)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}

def test_update_profile_settings(client, test_user, auth_headers):
    payload = {
        "public_username": "newuser",
        "bio": "I am a cave man",
        "visibility": "public"
    }
    response = client.patch("/api/profile/settings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["data"]["public_username"] == "newuser"
    assert data["data"]["bio"] == "I am a cave man"
    assert data["data"]["visibility"] == "public"

def test_update_username_conflict(client, app, test_user, auth_headers):
    with app.app_context():
        other = User(email="other@iqoqo.local", public_username="taken")
        db.session.add(other)
        db.session.commit()
    
    response = client.patch("/api/profile/settings", json={"public_username": "taken"}, headers=auth_headers)
    assert response.status_code == 409

def test_toggle_item_visibility(client, app, test_user, auth_headers):
    with app.app_context():
        work = Work(title="Visibility Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(mani)
        db.session.flush()
        item = Item(owner_id=test_user, manifestation_id=mani.id, is_hidden=False)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Hide
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": True}, headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["is_hidden"] is True

    # Show
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": False}, headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["is_hidden"] is False

def test_toggle_item_visibility_unauthorized(client, app, test_user):
    with app.app_context():
        # Create item for test_user
        work = Work(title="Spy Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="1234567890124")
        db.session.add(mani)
        db.session.flush()
        item = Item(owner_id=test_user, manifestation_id=mani.id)
        db.session.add(item)
        
        # Create another user
        other = User(email="spy@iqoqo.local")
        db.session.add(other)
        db.session.commit()
        item_id = item.id
        other_token = generate_internal_jwt(other)
    
    headers = {"Authorization": f"Bearer {other_token}"}
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": True}, headers=headers)
    assert response.status_code == 404 # BOLA protection
