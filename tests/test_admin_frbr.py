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

"""Tests for the FRBR entity management API endpoints."""

from app.core import frbr_service
from app.db.core import Expression, Item, Manifestation, Work, db


def test_get_frbr_tree_unauthorized(client):
    """Ensure unauthenticated users are blocked."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/1")
    assert res.status_code in [401, 403]


def test_get_frbr_tree_forbidden(client, normal_user_headers):
    """Ensure non-admin users get forbidden."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/1", headers=normal_user_headers)
    assert res.status_code in [401, 403]


def test_get_frbr_tree_not_found(client, admin_headers):
    """Ensure 404 is returned for non-existent manifestation."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/999999", headers=admin_headers)
    assert res.status_code == 404
    assert res.json["success"] is False


def test_get_frbr_tree_success(client, admin_headers, app):
    """Test fetching the full FRBR tree for a manifestation."""
    with app.app_context():
        # Create a complete FRBR hierarchy
        work = frbr_service.create_work(title="Test FRBR Book")
        expression = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        manifestation = frbr_service.create_manifestation(
            expression_id=expression.id,
            isbn13="9781234567890",
            publisher="Test Publisher",
            meta={"TestMeta": "test_value"}
        )
        work_id = work.id
        manif_id = manifestation.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True

    data = res.json["data"]
    assert data["work"]["title"] == "Test FRBR Book"
    assert data["work"]["id"] == work_id
    assert data["expression"]["content_type"] == "text"
    assert data["expression"]["language"] == "en"
    assert data["manifestation"]["isbn13"] == "9781234567890"
    assert data["manifestation"]["publisher"] == "Test Publisher"


def test_get_frbr_tree_with_items(client, admin_headers, app):
    """Test fetching FRBR tree including items."""
    with app.app_context():
        from app.db.models import User

        # Create work, expression, manifestation
        work = frbr_service.create_work(title="Book with Items")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(expression_id=expression.id, isbn13="111")

        # Get a test user for item ownership
        user = User.query.first()
        if not user:
            user = User(email="item_owner@iqoqo.local", display_name="Item Owner")
            db.session.add(user)
            db.session.commit()

        # Create items using direct Item creation to use UUID
        item1 = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", meta={})
        item2 = Item(manifestation_id=manifestation.id, owner_id=user.id, status="lent", meta={})
        db.session.add_all([item1, item2])
        db.session.commit()
        manif_id = manifestation.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json["data"]
    assert len(data["items"]) == 2
    assert data["items"][0]["status"] == "available"
    assert data["items"][1]["status"] == "lent"


def test_update_work(client, admin_headers, app):
    """Test updating a Work entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Original Title", meta={"original_key": "original_value"})
        work_id = work.id

    res = client.put(
        f"/api/v1/admin/frbr/work/{work_id}",
        json={"title": "Updated Title", "meta": {"new_key": "new_value"}},
        headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["id"] == work_id

    # Verify the update in the database
    with app.app_context():
        updated_work = db.session.get(Work, work_id)
        assert updated_work.title == "Updated Title"
        assert updated_work.meta["original_key"] == "original_value"
        assert updated_work.meta["new_key"] == "new_value"


def test_update_expression(client, admin_headers, app):
    """Test updating an Expression entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        expr_id = expression.id

    res = client.put(
        f"/api/v1/admin/frbr/expression/{expr_id}",
        json={"content_type": "audio", "language": "pl", "meta": {"TrackCount": 10}},
        headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.content_type == "audio"
        assert updated_expr.language == "pl"
        assert updated_expr.meta["TrackCount"] == 10


def test_update_manifestation(client, admin_headers, app):
    """Test updating a Manifestation entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(
            expression_id=expression.id,
            isbn13="9780000000000",
            publisher="Original Publisher"
        )
        manif_id = manifestation.id

    res = client.put(
        f"/api/v1/admin/frbr/manifestation/{manif_id}",
        json={
            "isbn13": "9781111111111",
            "publisher": "New Publisher",
            "meta": {"Pages": 300}
        },
        headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_manif = db.session.get(Manifestation, manif_id)
        assert updated_manif.isbn13 == "9781111111111"
        assert updated_manif.publisher == "New Publisher"
        assert updated_manif.meta["Pages"] == 300


def test_update_item(client, admin_headers, app):
    """Test updating an Item entity."""
    with app.app_context():
        from app.db.models import User

        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(expression_id=expression.id)

        user = User.query.first()
        if not user:
            user = User(email="item_test@iqoqo.local", display_name="Item Test")
            db.session.add(user)
            db.session.commit()

        # Use direct Item creation to use UUID
        item = Item(
            manifestation_id=manifestation.id,
            owner_id=user.id,
            status="available",
            condition="Like New",
            meta={}
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    res = client.put(
        f"/api/v1/admin/frbr/item/{item_id}",
        json={"status": "lent", "condition": "Fair", "meta": {"LentTo": "Friend"}},
        headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_item = db.session.get(Item, item_id)
        assert updated_item.status == "lent"
        assert updated_item.condition == "Fair"
        assert updated_item.meta["LentTo"] == "Friend"


def test_update_work_not_found(client, admin_headers):
    """Test updating non-existent work returns 404."""
    res = client.put(
        "/api/v1/admin/frbr/work/999999",
        json={"title": "New Title"},
        headers=admin_headers
    )
    assert res.status_code == 404
    assert res.json["success"] is False


def test_update_expression_invalid_work(client, admin_headers, app):
    """Test updating expression with invalid work_id returns 404."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        expr_id = expression.id

    res = client.put(
        f"/api/v1/admin/frbr/expression/{expr_id}",
        json={"work_id": 999999},
        headers=admin_headers
    )
    assert res.status_code == 404
    assert res.json["success"] is False


def test_search_frbr_manifestation_by_isbn(client, admin_headers, app):
    """Test searching manifestations by ISBN."""
    with app.app_context():
        work = frbr_service.create_work(title="Searchable Book")
        expression = frbr_service.create_expression(work_id=work.id)
        frbr_service.create_manifestation(expression_id=expression.id, isbn13="9781234567890")

    res = client.get("/api/v1/admin/frbr/search?q=9781234567890&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["isbn13"] == "9781234567890"


def test_search_frbr_manifestation_by_upc(client, admin_headers, app):
    """Test searching manifestations by UPC."""
    with app.app_context():
        work = frbr_service.create_work(title="UPC Book")
        expression = frbr_service.create_expression(work_id=work.id)
        frbr_service.create_manifestation(expression_id=expression.id, upc="123456789012")

    res = client.get("/api/v1/admin/frbr/search?q=123456789012&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["upc"] == "123456789012"


def test_search_frbr_work_by_title(client, admin_headers, app):
    """Test searching works by title."""
    with app.app_context():
        frbr_service.create_work(title="Unique Work Title XYZ")

    res = client.get("/api/v1/admin/frbr/search?q=Unique Work Title XYZ&type=work", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["title"] == "Unique Work Title XYZ"


def test_search_frbr_empty_query(client, admin_headers):
    """Test search with empty query returns empty results."""
    res = client.get("/api/v1/admin/frbr/search?q=&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"] == []
