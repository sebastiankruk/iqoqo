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
from app.db.auth import User
from app.db.core import UserCollection, db


@pytest.fixture
def test_user(app):
    """Create a test user for collection tests."""
    with app.app_context():
        user = User(email="collection_test@iqoqo.local", display_name="Collection Tester")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        # Ensure ID is loaded before it becomes detached
        _ = user.id
        return user


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers for the test user."""
    token = generate_internal_jwt(test_user)
    return {"Authorization": f"Bearer {token}"}


def test_list_collections(client, auth_headers, test_user, app):
    """Test retrieving all collections for the authenticated user."""
    with app.app_context():
        col1 = UserCollection(owner_id=test_user.id, name="Sci-Fi")
        db.session.add(col1)
        db.session.commit()

    response = client.get("/api/collections", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["collections"]) >= 1
    assert any(c["name"] == "Sci-Fi" for c in data["collections"])


def test_create_collection_success(client, auth_headers):
    """Test successful creation of a parent and a child collection."""
    # Parent
    res1 = client.post("/api/collections", json={"name": "Fantasy"}, headers=auth_headers)
    assert res1.status_code == 201
    parent_id = res1.get_json()["collection"]["id"]

    # Child
    res2 = client.post("/api/collections", json={"name": "High Fantasy", "parent_id": parent_id}, headers=auth_headers)
    assert res2.status_code == 201
    assert res2.get_json()["collection"]["parent_id"] == parent_id


def test_create_collection_invalid_payload(client, auth_headers):
    """Test validation blocks empty names."""
    # Note: Pydantic schema validation might return different error structure
    response = client.post("/api/collections", json={"name": ""}, headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_update_collection(client, auth_headers, test_user, app):
    """Test renaming a collection and checking cyclic parent logic."""
    with app.app_context():
        col = UserCollection(owner_id=test_user.id, name="Old Name")
        db.session.add(col)
        db.session.commit()
        col_id = col.id

    # Valid Rename
    res1 = client.put(f"/api/collections/{col_id}", json={"name": "New Name"}, headers=auth_headers)
    assert res1.status_code == 200
    assert res1.get_json()["collection"]["name"] == "New Name"

    # Invalid Parent (Cannot be its own parent)
    res2 = client.put(f"/api/collections/{col_id}", json={"parent_id": col_id}, headers=auth_headers)
    assert res2.status_code == 400
    assert "own parent" in res2.get_json()["error"]


def test_delete_collection_with_children(client, auth_headers, test_user, app):
    """Test protection against deleting collections that have nested children."""
    with app.app_context():
        parent = UserCollection(owner_id=test_user.id, name="Parent")
        db.session.add(parent)
        db.session.commit()
        parent_id = parent.id

        child = UserCollection(owner_id=test_user.id, name="Child", parent_id=parent_id)
        db.session.add(child)
        db.session.commit()
        child_id = child.id

    # Attempt to delete parent
    response = client.delete(f"/api/collections/{parent_id}", headers=auth_headers)
    assert response.status_code == 400
    assert "sub-collections" in response.get_json()["error"]

    # Delete child first, then parent should succeed
    client.delete(f"/api/collections/{child_id}", headers=auth_headers)
    response2 = client.delete(f"/api/collections/{parent_id}", headers=auth_headers)
    assert response2.status_code == 200
