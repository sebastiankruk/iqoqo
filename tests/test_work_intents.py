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

import secrets

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

    # Filter items by wish_list (collection-level status)
    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    wish_items = [i for i in response.json["data"] if i.get("is_virtual")]
    assert len(wish_items) == 1
    assert wish_items[0]["title"] == "Test Conceptual Work"
    assert wish_items[0]["collection_status"] == "wish_list"

    # Filter by specific intent-level status
    response = client.get("/api/items?statuses=want_to_read", headers=headers)
    assert response.status_code == 200
    want_items = [i for i in response.json["data"] if i.get("is_virtual")]
    assert len(want_items) == 1
    assert want_items[0]["status"] == "want_to_read"

    # Non-matching status should NOT include virtual items
    response = client.get("/api/items?statuses=available", headers=headers)
    assert response.status_code == 200
    avail_virtual = [i for i in response.json["data"] if i.get("is_virtual")]
    assert len(avail_virtual) == 0


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
    assert data["item_id"] is None
    assert data["intent_id"] > 0

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
        # UserWorkIntent fulfilled, not deleted
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is not None
        assert intent.status == "fulfilled"

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


def test_transition_virtual_to_physical(client, test_setup, app):
    """Verify transition from virtual intent to physical item."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # Create intent
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        virtual_item_id = -intent.id

    # Transition to physical
    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"collection_status": "available", "status": "read"},
        headers=headers,
    )
    assert response.status_code == 200
    physical_item_id = response.json["data"]["id"]
    assert physical_item_id > 0

    with app.app_context():
        # UserWorkIntent not deleted, marked as fulfilled
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is not None
        assert intent.status == "fulfilled"

        # Physical Item created
        item = db.session.get(Item, physical_item_id)
        assert item is not None
        assert item.collection_status == "available"
        assert item.status == "read"
        assert item.meta.get("intent_id") == -virtual_item_id


def test_delete_virtual_item(client, test_setup, app):
    """Verify delete of virtual intent."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    # Create intent
    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        virtual_item_id = -intent.id

    # Delete intent
    response = client.delete(f"/api/items/{virtual_item_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        assert intent is None


def test_transition_nonexistent_virtual_item(client, test_setup, app):
    """Verify transition of non-existent virtual item returns 404."""
    headers = get_headers(app, test_setup["user_id"])
    response = client.put(
        "/api/items/-99999",
        json={"collection_status": "available", "status": "read"},
        headers=headers,
    )
    assert response.status_code == 404


def test_transition_invalid_payload(client, test_setup, app):
    """Verify transition with malformed collection_status returns 400."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        virtual_item_id = -intent.id

    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"collection_status": "invalid_c_status", "status": "read"},
        headers=headers,
    )
    assert response.status_code == 400


def test_transition_unauthorized(client, test_setup, app):
    """Verify transition of other user's virtual item returns 403."""
    headers = get_headers(app, test_setup["user_id"])
    work_id = test_setup["work_id"]

    client.post(
        f"/api/works/{work_id}/intent",
        json={"status": "want_to_read"},
        headers=headers,
    )

    with app.app_context():
        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=work_id).first()
        virtual_item_id = -intent.id

    # Create another user and headers
    with app.app_context():
        other_user = User(email="other@iqoqo.local")
        db.session.add(other_user)
        db.session.commit()
        other_user_id = other_user.id

    other_headers = get_headers(app, other_user_id)

    # Attempt to transition other user's intent
    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"collection_status": "available", "status": "read"},
        headers=other_headers,
    )
    assert response.status_code == 403


# --- Phase 2: Bug B8 — Virtual items visible without manifestation ---


def test_virtual_items_visible_without_manifestation(client, app):
    """B8: Works without Manifestation should still appear as virtual items."""
    with app.app_context():
        user = User(email="b8_test@iqoqo.local", display_name="B8 Tester")
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.flush()
        perm = Permission.query.filter_by(name="write:item").first()
        if not perm:
            perm = Permission(name="write:item")
            db.session.add(perm)
        if perm not in role.permissions:
            role.permissions.append(perm)
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()

        # Create Work with NO expressions/manifestations
        work = Work(title="Orphan Wishlist Book", meta={"authors": []})
        db.session.add(work)
        db.session.flush()

        # Create intent
        intent = UserWorkIntent(work_id=work.id, user_id=user.id, status="want_to_read")
        db.session.add(intent)
        db.session.commit()

        token = generate_internal_jwt(user)
        headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/items?statuses=want_to_read", headers=headers)
    assert resp.status_code == 200
    items = resp.get_json()["data"]
    virtual = [i for i in items if i.get("is_virtual") and i["title"] == "Orphan Wishlist Book"]
    assert len(virtual) == 1
    assert virtual[0]["id"] < 0


def test_virtual_items_with_category_filter_no_manifestation(client, app):
    """B8: Category filter should not eliminate manifestation-less intents."""
    with app.app_context():
        user = User(email="b8_cat_test@iqoqo.local", display_name="B8 Cat Tester")
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.flush()
        perm = Permission.query.filter_by(name="write:item").first()
        if not perm:
            perm = Permission(name="write:item")
            db.session.add(perm)
        if perm not in role.permissions:
            role.permissions.append(perm)
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()

        # Create Work with NO expressions/manifestations
        work = Work(title="Filtered Orphan", meta={"authors": []})
        db.session.add(work)
        db.session.flush()

        intent = UserWorkIntent(work_id=work.id, user_id=user.id, status="want_to_read")
        db.session.add(intent)
        db.session.commit()

        token = generate_internal_jwt(user)
        headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        "/api/items?statuses=want_to_read&category=text",
        headers=headers,
    )
    assert resp.status_code == 200
    items = resp.get_json()["data"]
    virtual = [i for i in items if i.get("is_virtual") and i["title"] == "Filtered Orphan"]
    assert len(virtual) == 1


def test_virtual_item_detail_no_manifestation(client, app):
    """B8: GET /api/items/<negative_id> returns work details even when there's no manifestation."""
    with app.app_context():
        user = User(email="b8_detail_test@iqoqo.local", display_name="B8 Detail Tester")
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
            db.session.flush()
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()

        work = Work(title="B8 Detail Orphan", meta={"authors": ["Detail Author"]})
        db.session.add(work)
        db.session.flush()

        intent = UserWorkIntent(work_id=work.id, user_id=user.id, status="want_to_read")
        db.session.add(intent)
        db.session.commit()

        token = generate_internal_jwt(user)
        headers = {"Authorization": f"Bearer {token}"}
        intent_id = intent.id

    resp = client.get(f"/api/items/{-intent_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["id"] == -intent_id
    assert data["manifestation_id"] is None
    assert data["work"]["title"] == "B8 Detail Orphan"
    assert data["work"]["authors"] == ["Detail Author"]


def test_add_to_wishlist_by_manifestation(client, test_setup, app):
    """POST /api/manifestations/<id>/add with wish_list collection status creates UserWorkIntent."""
    headers = get_headers(app, test_setup["user_id"])
    manif_id = test_setup["manifestation_id"]

    response = client.post(
        f"/api/manifestations/{manif_id}/add",
        json={"collection_status": "wish_list"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert data["manifestation_id"] == manif_id
    assert data["item_id"] is None
    assert data["intent_id"] > 0

    with app.app_context():
        items = Item.query.filter_by(manifestation_id=manif_id, owner_id=test_setup["user_id"]).all()
        assert len(items) == 0

        intent = UserWorkIntent.query.filter_by(user_id=test_setup["user_id"], work_id=test_setup["work_id"]).first()
        assert intent is not None
        assert intent.status == "want_to_read"


# --- Phase 2: Virtual item visibility (is_hidden + auth) ---


def _make_virtual_item(app, user_id, status="want_to_read", is_hidden=False):
    """Helper: create a Work + UserWorkIntent, return virtual_item_id."""
    with app.app_context():
        work = Work(title=f"Visibility Work {secrets.token_hex(4)}", meta={"authors": ["Test"]})
        db.session.add(work)
        db.session.flush()
        intent = UserWorkIntent(user_id=user_id, work_id=work.id, status=status, is_hidden=is_hidden)
        db.session.add(intent)
        db.session.commit()
        return -intent.id


def test_virtual_item_is_hidden_field(client, test_setup, app):
    """PATCH /api/items/<negative_id>/visibility toggles is_hidden on intent."""
    with app.app_context():
        user = User.query.filter_by(email="intent_test@iqoqo.local").first()
    headers = get_headers(app, user.id)
    virtual_item_id = _make_virtual_item(app, user.id, is_hidden=False)

    # Hide
    response = client.patch(
        f"/api/items/{virtual_item_id}/visibility",
        json={"is_hidden": True},
        headers=headers,
    )
    assert response.status_code == 200

    with app.app_context():
        intent_id = -virtual_item_id
        intent = db.session.get(UserWorkIntent, intent_id)
        assert intent.is_hidden is True

    # Unhide
    response = client.patch(
        f"/api/items/{virtual_item_id}/visibility",
        json={"is_hidden": False},
        headers=headers,
    )
    assert response.status_code == 200

    with app.app_context():
        intent = db.session.get(UserWorkIntent, -virtual_item_id)
        assert intent.is_hidden is False


def test_virtual_item_owner_always_sees_hidden(client, test_setup, app):
    """Owner sees hidden virtual items in both list and detail views."""
    with app.app_context():
        user = User.query.filter_by(email="intent_test@iqoqo.local").first()
    headers = get_headers(app, user.id)
    virtual_item_id = _make_virtual_item(app, user.id, is_hidden=True)

    # List view shows hidden intent for owner
    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    visible = [i for i in response.json["data"] if i.get("is_virtual") and i["id"] == virtual_item_id]
    assert len(visible) == 1
    assert visible[0]["is_hidden"] is True

    # Detail view works for owner
    response = client.get(f"/api/items/{virtual_item_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["is_hidden"] is True
    assert response.json["data"]["is_owner"] is True


def test_virtual_item_hidden_from_non_owner(client, test_setup, app):
    """Non-owner gets 404 for hidden virtual item detail."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="voyeur@iqoqo.local", display_name="Voyeur")
        db.session.add(other)
        db.session.commit()

        owner_headers = get_headers(app, owner_id)
        other_headers = get_headers(app, other.id)

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=True)

    # Non-owner gets 404 for hidden virtual item detail
    response = client.get(f"/api/items/{virtual_item_id}", headers=other_headers)
    assert response.status_code == 404

    # Owner can still see it
    response = client.get(f"/api/items/{virtual_item_id}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json["data"]["is_owner"] is True


def test_virtual_item_visible_to_non_owner_when_not_hidden(client, test_setup, app):
    """Non-owner can see non-hidden virtual item detail (wishlist sharing)."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="friend@iqoqo.local", display_name="Friend")
        db.session.add(other)
        db.session.commit()

        owner_headers = get_headers(app, owner_id)
        other_headers = get_headers(app, other.id)

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=False)

    # Non-owner can see non-hidden virtual item detail
    response = client.get(f"/api/items/{virtual_item_id}", headers=other_headers)
    assert response.status_code == 200
    assert response.json["data"]["is_owner"] is False

    # Owner still sees it as owner
    response = client.get(f"/api/items/{virtual_item_id}", headers=owner_headers)
    assert response.status_code == 200
    assert response.json["data"]["is_owner"] is True


def test_virtual_item_anonymous_gets_404(client, test_setup, app):
    """Anonymous user gets 404 for virtual item detail (must authenticate)."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=False)

    # No auth header -> 404 (not 401!)
    response = client.get(f"/api/items/{virtual_item_id}")
    assert response.status_code == 404


def test_virtual_item_anonymous_gets_404_even_when_hidden(client, test_setup, app):
    """Anonymous gets 404 regardless of hidden state — consistent BOLA."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=True)

    response = client.get(f"/api/items/{virtual_item_id}")
    assert response.status_code == 404


def test_virtual_item_hidden_not_in_non_owner_list(client, test_setup, app):
    """Hidden virtual items do not appear in non-owner's item list."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="listchecker@iqoqo.local", display_name="List Checker")
        db.session.add(other)
        db.session.commit()

        other_headers = get_headers(app, other.id)

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=True)

    # Non-owner list should not include hidden virtual items
    response = client.get("/api/items", headers=other_headers)
    assert response.status_code == 200
    virtual = [i for i in response.json["data"] if i.get("is_virtual") and i["id"] == virtual_item_id]
    assert len(virtual) == 0


def test_virtual_item_update_uses_verify_item_ownership(client, test_setup, app):
    """Non-owner gets 403 when trying to update another user's virtual item."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="updater@iqoqo.local", display_name="Updater")
        db.session.add(other)
        db.session.commit()

        other_headers = get_headers(app, other.id)

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=False)

    response = client.put(
        f"/api/items/{virtual_item_id}",
        json={"status": "reading"},
        headers=other_headers,
    )
    assert response.status_code == 403


def test_virtual_item_delete_uses_verify_item_ownership(client, test_setup, app):
    """Non-owner gets 403 when trying to delete another user's virtual item."""
    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="deleter@iqoqo.local", display_name="Deleter")
        db.session.add(other)
        db.session.commit()

        other_headers = get_headers(app, other.id)

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=False)

    response = client.delete(f"/api/items/{virtual_item_id}", headers=other_headers)
    assert response.status_code == 403


def test_delete_virtual_item_helper_inline_ownership(app, client, test_setup):
    """_delete_virtual_item rejects non-owner even when called directly (no decorator)."""
    from app.api.items import _delete_virtual_item

    with app.app_context():
        owner = User.query.filter_by(email="intent_test@iqoqo.local").first()
        owner_id = owner.id
        other = User(email="direct_del@iqoqo.local", display_name="Direct Del")
        db.session.add(other)
        db.session.commit()
        other_id = other.id

    virtual_item_id = _make_virtual_item(app, owner_id, is_hidden=False)

    with app.test_request_context():
        response, status = _delete_virtual_item(virtual_item_id, other_id)
        assert status == 403
        assert response.json["error"] == "Forbidden"


def test_delete_physical_item_helper_inline_ownership(app, client, admin_headers):
    """_delete_physical_item rejects non-owner even when called directly (no decorator)."""
    from app.api.items import _delete_physical_item

    with app.app_context():
        owner = User(email="phys_owner@iqoqo.local", display_name="Phys Owner")
        other = User(email="phys_del@iqoqo.local", display_name="Phys Del")
        db.session.add_all([owner, other])
        db.session.flush()

        work = Work(title="Physical Delete Test", meta={"authors": ["Test"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000099")
        db.session.add(manif)
        db.session.flush()
        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available")
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        other_id = other.id

    with app.test_request_context():
        response, status = _delete_physical_item(item_id, other_id)
        assert status == 403
        assert response.json["error"] == "Forbidden"
