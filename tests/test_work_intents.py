# tests/test_work_intents.py
"""Tests for Conceptual Work (F1) Level Intents and dynamic synthesis."""

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
from app.core.data_manager import DataManager
from app.db import db
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, UserWorkIntent, Work


@pytest.fixture
def test_setup(app):
    """Seed database with a work, expression, manifestation, and user."""
    with app.app_context():
        # Create user role and write:item permission so that scan works
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)

        write_item_perm = Permission.query.filter_by(name="write:item").first()
        if not write_item_perm:
            write_item_perm = Permission(name="write:item")
            db.session.add(write_item_perm)

        if write_item_perm not in user_role.permissions:
            user_role.permissions.append(write_item_perm)

        delete_item_perm = Permission.query.filter_by(name="delete:item").first()
        if not delete_item_perm:
            delete_item_perm = Permission(name="delete:item")
            db.session.add(delete_item_perm)

        if delete_item_perm not in user_role.permissions:
            user_role.permissions.append(delete_item_perm)

        # Create a test user
        user = User(email="intent_test@iqoqo.local", display_name="Intent Tester")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Create a work
        work = Work(title="Test Conceptual Work", meta={"authors": ["Test Author"]})
        db.session.add(work)
        db.session.flush()

        # Create expression
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        # Create manifestation
        manif = Manifestation(expression_id=expr.id, isbn13="9781234567890", meta={"format": "book"})
        db.session.add(manif)
        db.session.flush()

        db.session.commit()
        return {
            "user_id": user.id,
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
        }


def get_headers(app, user_id):
    """Generate auth headers for a user."""
    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


def test_get_work_intent_not_found(client, test_setup, app):
    """GET /api/works/<work_id>/intent returns 404 if work doesn't exist."""
    headers = get_headers(app, test_setup["user_id"])
    response = client.get("/api/works/999999/intent", headers=headers)
    assert response.status_code == 404
    assert "Work not found" in response.json["error"]


def test_get_work_intent_empty(client, test_setup, app):
    """GET /api/works/<work_id>/intent returns null status if no intent exists."""
    headers = get_headers(app, test_setup["user_id"])
    response = client.get(f"/api/works/{test_setup['work_id']}/intent", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["status"] is None


def test_set_and_delete_work_intent(client, test_setup, app):
    """POST and DELETE /api/works/<work_id>/intent manages intents correctly."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # POST to set intent
    response = client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["status"] == "want_to_read"

    # Verify intent in DB
    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is not None
        assert intent.status == "want_to_read"

    # GET intent
    response = client.get(f"/api/works/{work_id}/intent", headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["status"] == "want_to_read"

    # POST to update intent
    response = client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "reading"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["data"]["status"] == "reading"

    # POST with invalid status returns 400
    response = client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "invalid_status"},
        headers=headers,
    )
    assert response.status_code == 400

    # DELETE to remove intent
    response = client.delete(f"/api/works/{work_id}/intent", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["status"] is None

    # Verify deleted in DB
    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is None


def test_dynamic_virtual_item_synthesis(client, test_setup, app):
    """GET /api/items dynamically synthesizes virtual wishlist items."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # Set intent
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    # Get items without filter (should include synthesized item)
    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    # We should have at least 1 item (the synthesized virtual item)
    virtual_items = [item for item in data if item.get("is_virtual")]
    assert len(virtual_items) == 1
    v_item = virtual_items[0]
    assert v_item["title"] == "Test Conceptual Work"
    assert v_item["collection_status"] == "wish_list"
    assert v_item["status"] == "want_to_read"
    assert v_item["manifestation_id"] == test_setup["manifestation_id"]
    assert v_item["id"] < 0  # Synthesized negative ID

    # Filter items by wish_list
    response = client.get("/api/items?status=wish_list", headers=headers)
    assert response.status_code == 200
    assert len(response.json["data"]) == 1
    assert response.json["data"][0]["title"] == "Test Conceptual Work"


def test_scanner_wishlist_ingest(client, test_setup, app):
    """POST /api/scan with wish_list collection status creates work intent, not physical item."""
    headers = get_headers(app, test_setup["user_id"])
    manif_id = test_setup["manifestation_id"]

    # Trigger scan wishlist ingestion
    response = client.post(
        "/api/scan",
        json={"manifestation_id": manif_id, "collection_status": "wish_list"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json["data"]
    assert data["manifestation_id"] == manif_id
    assert data["item_id"] < 0  # returned negative virtual item id

    # Verify no physical item was created in DB
    with app.app_context():
        items = Item.query.filter_by(manifestation_id=manif_id, owner_id=test_setup["user_id"]).all()
        assert len(items) == 0

        # Verify UserWorkIntent was created in DB
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=test_setup["work_id"]).first()
        assert intent is not None
        assert intent.status == "want_to_read"


def test_data_manager_stats_with_intents(client, test_setup, app):
    """DataManager.get_stats correctly counts UserWorkIntent records for wishlist."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # Initially stats should have 0 wishlist/to_read
    with app.app_context():
        stats = DataManager.get_stats(test_setup["user_id"])
        assert stats["to_read"] == 0
        assert stats["items_wish_list"] == 0

    # Set intent
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    # Get stats and verify
    with app.app_context():
        stats = DataManager.get_stats(test_setup["user_id"])
        assert stats["to_read"] == 1
        assert stats["items_wish_list"] == 1
        # Work count is 1 (the wanted book is part of user scoped count)
        assert stats["works"] == 1


def test_virtual_item_detail_update_delete(client, test_setup, app):
    """GET, PUT, and DELETE /api/items/<negative_id> operates correctly for virtual items."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # Set intent
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    # Get intent ID
    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is not None
        virtual_item_id = -intent.id

    # 1. GET detail
    response = client.get(f"/api/items/{virtual_item_id}", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["id"] == virtual_item_id
    assert data["collection_status"] == "wish_list"
    assert data["status"] == "want_to_read"
    assert data["work"]["title"] == "Test Conceptual Work"

    # 2. PUT update (only status)
    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"status": "reading"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["data"]["id"] == virtual_item_id

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent.status == "reading"

    # 3. PUT update (transition to physical library)
    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"collection_status": "available", "status": "read"},
        headers=headers,
    )
    assert response.status_code == 200
    physical_item_id = response.json["data"]["id"]
    assert physical_item_id > 0

    with app.app_context():
        # UserWorkIntent deleted
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is None

        # Physical Item created
        item = db.session.get(Item, physical_item_id)
        assert item is not None
        assert item.collection_status == "available"
        assert item.status == "read"

    # 4. DELETE virtual item
    # Re-create intent first
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )
    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        virtual_item_id = -intent.id

    response = client.delete(f"/api/items/{virtual_item_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is None
