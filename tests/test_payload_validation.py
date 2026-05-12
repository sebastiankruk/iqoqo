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
"""Tests for API security and payload validation."""

import uuid

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, Role, User, Work, db


@pytest.fixture
def user_with_item(app):
    with app.app_context():
        user = User(email="test@example.com", display_name="Test User")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        m = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(m)
        db.session.flush()

        item = Item(owner_id=user.id, manifestation_id=m.id, status="available", collection_status="available")
        db.session.add(item)
        db.session.commit()

        token = generate_internal_jwt(user)
        return user.id, item.id, {"Authorization": f"Bearer {token}"}


def test_update_item_bola_prevention(client, user_with_item):
    _, item_id, headers = user_with_item

    # Try to inject owner_id
    payload = {"status": "reading", "owner_id": str(uuid.uuid4())}
    response = client.put(f"/api/items/{item_id}", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid payload" in response.json["error"]


def test_update_item_valid(client, user_with_item):
    _, item_id, headers = user_with_item

    payload = {"status": "reading"}
    response = client.put(f"/api/items/{item_id}", json=payload, headers=headers)
    assert response.status_code == 200

    with client.application.app_context():
        updated_item = db.session.get(Item, item_id)
        assert updated_item.status == "reading"


def test_add_item_manual_extra_fields(client, normal_user_headers):
    payload = {
        "Title": "Test Book",
        "Authors": ["Author A"],
        "Format": "text",
        "Year": "2024",  # Extra field
        "CustomField": "CustomValue",  # Extra field
    }
    # Add manual item via POST
    # Actually add_item_manual is POST
    response = client.post("/api/items/manual", json=payload, headers=normal_user_headers)
    assert response.status_code == 200

    m_id = response.json["data"]["manifestation_id"]
    with client.application.app_context():
        m = db.session.get(Manifestation, m_id)
        assert m.meta["Year"] == "2024"
        assert m.meta["CustomField"] == "CustomValue"


def test_scan_barcode_invalid_payload(client, normal_user_headers):
    payload = {"barcode": "123456", "unknown": "value"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 400
    assert "Invalid payload" in response.json["error"]


@pytest.fixture
def app_with_limiter(app):
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    # Re-init to pick up config
    limiter.init_app(app)
    return app


def test_admin_required_refactored(client, app):
    # Create normal user
    with app.app_context():
        user = User(email="normal@example.com")
        db.session.add(user)
        db.session.commit()
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}
    # Correct path is /api/v1/admin/users
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403
    assert "Admin privileges required" in response.json["error"]


def test_lookup_rate_limit(app_with_limiter, normal_user_headers):
    client = app_with_limiter.test_client()
    # Hit it 10 times (limit is 10 per minute)
    for _ in range(10):
        response = client.get("/api/lookup/123", headers=normal_user_headers)
        # We accept 200 or 404 (not found) as long as it is not 429 (rate limited)
        assert response.status_code in (200, 404)

    # 11th should fail
    response = client.get("/api/lookup/123", headers=normal_user_headers)
    assert response.status_code == 429


def test_update_manifestation_security(client, normal_user_headers, admin_headers, app):
    # Setup: Create a manifestation
    isbn = "9780141036144"
    with app.app_context():
        work = Work(title="Old Title")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        m = Manifestation(expression_id=expr.id, isbn13=isbn)
        db.session.add(m)
        db.session.commit()

    # Anonymous update should fail
    response = client.post(f"/api/isbn/{isbn}", json={"Title": "Hacker Title"})
    assert response.status_code == 401

    # Normal user without permission should fail
    response = client.post(f"/api/isbn/{isbn}", json={"Title": "Sneaky Title"}, headers=normal_user_headers)
    assert response.status_code == 403

    # Admin user (with permission) should succeed
    response = client.post(f"/api/isbn/{isbn}", json={"Title": "Hardened Title"}, headers=admin_headers)
    assert response.status_code == 200


def test_update_manifestation_validation(client, admin_headers, app):
    isbn = "9780141036145"
    with app.app_context():
        work = Work(title="Validate Me")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        m = Manifestation(expression_id=expr.id, isbn13=isbn)
        db.session.add(m)
        db.session.commit()

    # Invalid Authors (string instead of list)
    response = client.post(f"/api/isbn/{isbn}", json={"Authors": "Not a list"}, headers=admin_headers)
    assert response.status_code == 400
    assert "Invalid payload" in response.json["error"]


def test_scan_barcode_dynamic_status(client, normal_user_headers, app):
    # Verify that collection_status can be passed dynamically
    barcode = "9780141036146"
    # Pre-mocking the manifestation lookup might be needed or just use a mock
    # But here we just want to see if the payload is accepted and processed
    payload = {"barcode": barcode, "collection_status": "wish_list"}
    # Note: /api/scan requires resolution, if it fails to resolve it might return 404
    # But the collection_status check happens before ingestion in some cases
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    # If it fails to resolve, it's 404/400, but we want to make sure it's not a payload error
    assert response.status_code != 400 or "Invalid payload" not in response.json.get("error", "")
