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
from app.db.core import UserCollection, UserCollectionItem, db
from app.db.models import Expression, Item, Manifestation, Permission, Role, Work


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


# ---------------------------------------------------------------------------
# Item-collection linking tests
# ---------------------------------------------------------------------------


@pytest.fixture
def item_linking_setup(app, test_user):
    """Set up an item, collection, and write:item permission for collection linking tests."""
    with app.app_context():
        write_item_perm = Permission.query.filter_by(name="write:item").first()
        if not write_item_perm:
            write_item_perm = Permission(name="write:item")
            db.session.add(write_item_perm)
            db.session.flush()

        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)
            db.session.flush()

        if write_item_perm not in user_role.permissions:
            user_role.permissions.append(write_item_perm)

        test_user_local = User.query.filter_by(id=test_user.id).first()
        if test_user_local and user_role not in test_user_local.roles:
            test_user_local.roles.append(user_role)
        db.session.flush()

        work = Work(title="Linking Test Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        man = Manifestation(expression_id=expr.id, meta={"format": "book"})
        db.session.add(man)
        db.session.flush()
        item = Item(manifestation_id=man.id, owner_id=test_user.id, status="available", collection_status="available")
        db.session.add(item)

        col = UserCollection(owner_id=test_user.id, name="My Shelf")
        db.session.add(col)

        db.session.commit()
        return {"item_id": item.id, "collection_id": col.id}


def test_get_item_collections_empty(client, auth_headers, item_linking_setup):
    """GET /items/<id>/collections returns empty when item has no collections."""
    item_id = item_linking_setup["item_id"]
    response = client.get(f"/api/items/{item_id}/collections", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["collections"] == []


def test_add_item_to_collection(client, auth_headers, item_linking_setup):
    """POST /items/<id>/collections links an item to a named collection."""
    item_id = item_linking_setup["item_id"]
    collection_id = item_linking_setup["collection_id"]

    response = client.post(
        f"/api/items/{item_id}/collections",
        json={"collection_id": collection_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # Verify via GET
    response = client.get(f"/api/items/{item_id}/collections", headers=auth_headers)
    collections = response.get_json()["data"]["collections"]
    assert len(collections) == 1
    assert collections[0]["name"] == "My Shelf"


def test_add_item_to_collection_duplicate(client, auth_headers, item_linking_setup):
    """POST /items/<id>/collections returns 409 for duplicate links."""
    item_id = item_linking_setup["item_id"]
    collection_id = item_linking_setup["collection_id"]

    # Add once
    client.post(f"/api/items/{item_id}/collections", json={"collection_id": collection_id}, headers=auth_headers)

    # Add again — should fail
    response = client.post(f"/api/items/{item_id}/collections", json={"collection_id": collection_id}, headers=auth_headers)
    assert response.status_code == 409


def test_remove_item_from_collection(client, auth_headers, item_linking_setup):
    """DELETE /items/<id>/collections/<cid> unlinks an item from a collection."""
    item_id = item_linking_setup["item_id"]
    collection_id = item_linking_setup["collection_id"]

    # Add first
    client.post(f"/api/items/{item_id}/collections", json={"collection_id": collection_id}, headers=auth_headers)

    # Remove
    response = client.delete(f"/api/items/{item_id}/collections/{collection_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # Verify empty
    response = client.get(f"/api/items/{item_id}/collections", headers=auth_headers)
    assert response.get_json()["data"]["collections"] == []


def test_remove_item_from_collection_not_found(client, auth_headers, item_linking_setup):
    """DELETE /items/<id>/collections/<cid> returns 404 for non-existent link."""
    item_id = item_linking_setup["item_id"]
    response = client.delete(f"/api/items/{item_id}/collections/99999", headers=auth_headers)
    assert response.status_code == 404


def test_add_item_to_collection_invalid_collection(client, auth_headers, item_linking_setup):
    """POST /items/<id>/collections returns 404 for non-existent collection."""
    item_id = item_linking_setup["item_id"]
    response = client.post(f"/api/items/{item_id}/collections", json={"collection_id": 99999}, headers=auth_headers)
    assert response.status_code == 404


def test_item_collections_forbidden_for_non_owner(client, app, auth_headers, item_linking_setup):
    """Non-owner cannot access another user's item collections."""
    with app.app_context():
        other_user = User(email="other_user@iqoqo.local", display_name="Other")
        db.session.add(other_user)
        db.session.flush()
        other_token = generate_internal_jwt(other_user)

    other_headers = {"Authorization": f"Bearer {other_token}"}
    item_id = item_linking_setup["item_id"]
    response = client.get(f"/api/items/{item_id}/collections", headers=other_headers)
    assert response.status_code == 403
