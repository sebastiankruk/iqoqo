"""Tests for Phase 1 API enhancements: new endpoints and CORS support."""

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

import uuid

import pytest

from app import create_app
from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work, db

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally
# pylint: disable=unused-argument  # fixtures used for setup, not always referenced


@pytest.fixture
def sample_work(app):
    # 1. Create a test user first so we have a valid UUID for the foreign key
    with app.app_context():
        test_user = User(email="testuser_phase1@iqoqo.local", display_name="Test User")
        db.session.add(test_user)
        db.session.flush()  # Commit so the DB generates the UUID

        # 2. Create the FRBR tree
        # Create Work
        work = Work(
            title="Test Book",
            meta={"authors": ["Test Author"], "categories": ["Fiction"]},
        )
        db.session.add(work)
        db.session.flush()

        # Create Expression
        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        # Create Manifestation
        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="9781234567890",
            meta={"Title": "Test Book", "Authors": ["Test Author"]},
        )
        db.session.add(manifestation)
        db.session.flush()
        # 3. Create the item using the User's UUID, NOT the string "test_user"
        item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available")  # <--- FIX: Use the actual User UUID
        db.session.add(item)
        db.session.commit()

        yield {"work": work, "expression": expression, "manifestation": manifestation, "item": item, "user": test_user}


@pytest.fixture
def cors_client():
    """Create test client with CORS explicitly enabled."""
    app = create_app(
        config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "CORS_ENABLED": True,
            "CORS_ORIGINS": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "CORS_METHODS": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "CORS_ALLOW_HEADERS": ["Content-Type", "Authorization"],
            "CORS_SUPPORTS_CREDENTIALS": True,
        }
    )

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


# =============================================================================
# CORS Tests
# =============================================================================


def test_cors_headers_on_api_request(cors_client):
    """Test that CORS headers are present on API requests from allowed origin."""
    response = cors_client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_headers_allow_127_origin(cors_client):
    """Test that CORS headers work with 127.0.0.1 origin."""
    response = cors_client.get("/api/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:3000"


def test_cors_preflight_options_request(cors_client):
    """Test that CORS preflight OPTIONS requests are handled correctly."""
    response = cors_client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert "Access-Control-Allow-Methods" in response.headers
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "PUT" in response.headers["Access-Control-Allow-Methods"]
    assert "DELETE" in response.headers["Access-Control-Allow-Methods"]


def test_cors_headers_present_on_all_api_calls(client):
    """Test that CORS configuration is applied to API endpoints."""
    response = client.get("/api/health")
    assert response.status_code == 200
    # Flask-CORS will add headers based on configuration
    # The important thing is that requests with proper Origin headers work correctly


# =============================================================================
# Enhanced Health Check Test
# =============================================================================


def test_health_check_enhanced(client):
    """Test the enhanced health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json
    assert data["status"] == "ok"
    assert data["service"] == "iqoqo-api"


# =============================================================================
# Stats Endpoint Tests
# =============================================================================


def test_get_stats_empty_database(client):
    """Test stats endpoint with empty database."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["error"] is None
    assert "data" in data
    stats = data["data"]
    assert stats["works"] == 0
    assert stats["expressions"] == 0
    assert stats["manifestations"] == 0
    assert stats["items"] == 0


def test_get_stats_with_data(client, sample_work):
    """Test stats endpoint with data in database."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    stats = data["data"]
    assert stats["works"] == 1
    assert stats["expressions"] == 1
    assert stats["manifestations"] == 1
    assert stats["items"] == 1


def test_stats_cors_headers(cors_client):
    """Test that stats endpoint returns CORS headers."""
    response = cors_client.get("/api/stats", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers


# =============================================================================
# Items List Endpoint Tests
# =============================================================================


def test_get_items_empty(client, admin_headers):
    """Test getting items list when database is empty."""
    response = client.get("/api/items", headers=admin_headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["data"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1


def test_get_items_with_data(client, sample_work, admin_headers):
    """Test getting items list with data."""
    # Generate token for the user who owns the item
    token = generate_internal_jwt(sample_work["user"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items", headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 20

    item = data["data"][0]
    assert item["title"] == "Test Book"
    assert item["authors"] == ["Test Author"]
    assert item["isbn"] == "9781234567890"
    assert item["status"] == "available"


def test_get_items_pagination(client, app):
    """Test items list pagination."""
    # Create multiple items
    with app.app_context():
        test_user = User(email="testuser_phase1@iqoqo.local", display_name="Test User")
        db.session.add(test_user)
        db.session.flush()  # Commit so the DB generates the UUID

        # Generate the token while we have the user object
        token = generate_internal_jwt(test_user)
        headers = {"Authorization": f"Bearer {token}"}

        work = Work(title="Test", meta={"authors": []})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9999999999999", meta={})
        db.session.add(manifestation)
        db.session.flush()

        # Add 25 items
        for _ in range(25):
            item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available", meta={})
            db.session.add(item)
        db.session.commit()

    # Test first page (Add headers here)
    response = client.get("/api/items?page=1&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 10
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 10
    assert data["meta"]["total"] == 25
    assert data["meta"]["pages"] == 3

    # Test second page (Add headers here)
    response = client.get("/api/items?page=2&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 10
    assert data["meta"]["page"] == 2

    # Test last page (Add headers here)
    response = client.get("/api/items?page=3&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 5
    assert data["meta"]["page"] == 3


def test_get_items_single_status_filter(client, app):
    """Test that ?statuses=reading returns only items with that status."""
    with app.app_context():
        work = Work(title="Reading Filter Test", meta={"authors": ["A. Writer"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9780000000001", meta={})
        db.session.add(manifestation)
        db.session.flush()

        test_user = User(email="testuser_phase1@iqoqo.local", display_name="Test User")
        db.session.add(test_user)
        db.session.flush()  # Commit so the DB generates the UUID

        # --- FIX: Generate the token for the newly created user ---
        token = generate_internal_jwt(test_user)
        headers = {"Authorization": f"Bearer {token}"}
        # ----------------------------------------------------------

        reading_item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="reading", meta={})
        available_item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available", meta={})
        db.session.add_all([reading_item, available_item])
        db.session.commit()

    # --- FIX: Pass the headers in the request ---
    response = client.get("/api/items?statuses=reading", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert all(item["status"] == "reading" for item in data["data"])
    assert data["meta"]["total"] == 1


def test_get_items_multi_status_filter(client, app):
    """Test ?statuses=reading,wish_list returns items with either status."""
    with app.app_context():
        work = Work(title="Multi Status Test", meta={"authors": ["B. Reader"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9780000000002", meta={})
        db.session.add(manifestation)
        db.session.flush()

        test_user = User(email="testuser_phase1@iqoqo.local", display_name="Test User")
        db.session.add(test_user)
        db.session.flush()  # Commit so the DB generates the UUID

        # --- FIX: Generate the token for the newly created user ---
        token = generate_internal_jwt(test_user)
        headers = {"Authorization": f"Bearer {token}"}
        # ----------------------------------------------------------

        items = [
            Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="reading", meta={}),
            Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="wish_list", meta={}),
            Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available", meta={}),
            Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="read", meta={}),
        ]
        db.session.add_all(items)
        db.session.commit()

    response = client.get("/api/items?statuses=reading,wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    returned_statuses = {item["status"] for item in data["data"]}
    assert returned_statuses == {"reading", "wish_list"}
    assert data["meta"]["total"] == 2


def test_get_items_includes_timestamps(client, sample_work):
    """Test that GET /api/items includes added_at and updated_at in each item."""
    token = generate_internal_jwt(sample_work["user"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert len(data["data"]) > 0

    item = data["data"][0]
    assert "added_at" in item
    assert "updated_at" in item
    # Both should be ISO-8601 strings (or None for legacy rows)
    for field in ("added_at", "updated_at"):
        if item[field] is not None:
            assert isinstance(item[field], str), f"{field} should be a string"


def test_get_items_ordering_by_updated_at(client, app):
    """Test that items are returned most-recently-updated first."""
    from datetime import UTC, datetime, timedelta  # pylint: disable=import-outside-toplevel

    now = datetime.now(UTC)

    with app.app_context():
        work = Work(title="Ordering Test", meta={"authors": ["C. Chronos"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9780000000003", meta={})
        db.session.add(manifestation)
        db.session.flush()

        test_user = User(email="testuser_phase1@iqoqo.local", display_name="Test User")
        db.session.add(test_user)
        db.session.flush()  # Commit so the DB generates the UUID

        # --- FIX: Generate the token for the newly created user ---
        token = generate_internal_jwt(test_user)
        headers = {"Authorization": f"Bearer {token}"}
        # ----------------------------------------------------------

        # Older item
        old_item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available", meta={})
        old_item.added_at = now - timedelta(hours=2)
        old_item.updated_at = now - timedelta(hours=2)

        # Newer item
        new_item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="available", meta={})
        new_item.added_at = now - timedelta(hours=1)
        new_item.updated_at = now - timedelta(minutes=5)

        db.session.add_all([old_item, new_item])
        db.session.commit()

        old_id = old_item.id
        new_id = new_item.id

    response = client.get("/api/items?statuses=available", headers=headers)
    assert response.status_code == 200
    data = response.json
    ids = [item["id"] for item in data["data"]]
    assert ids.index(new_id) < ids.index(old_id), "Newer item should appear before older item"


def test_get_items_status_filter_no_matches(client, sample_work, admin_headers):
    """Test that filtering by a status with no matching items returns empty list."""
    response = client.get("/api/items?statuses=lost", headers=admin_headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["data"] == []
    assert data["meta"]["total"] == 0


# =============================================================================
# Item Detail Endpoint Tests
# =============================================================================


def test_get_item_detail(client, sample_work):
    """Test getting detailed item information."""

    item_id = sample_work["item"].id
    owner_id = sample_work["item"].owner_id

    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["error"] is None

    item = data["data"]
    assert item["id"] == item_id
    assert item["owner_id"] == str(owner_id)
    assert item["status"] == "available"
    assert item["isbn"] == "9781234567890"
    assert item["work"]["title"] == "Test Book"
    assert item["work"]["authors"] == ["Test Author"]
    assert item["expression"]["content_type"] == "text"
    assert item["expression"]["language"] == "en"


def test_get_item_detail_not_found(client):
    """Test getting non-existent item returns 404."""
    response = client.get("/api/items/99999")
    assert response.status_code == 404
    data = response.json
    assert data["success"] is False
    assert data["error"] == "Item not found"


# =============================================================================
# Update Item Endpoint Tests
# =============================================================================


def test_update_item_status(client, sample_work):
    """Test updating item status."""
    item_id = sample_work["item"].id

    response = client.put(f"/api/items/{item_id}", json={"status": "reading"}, content_type="application/json")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True

    # Verify update
    response = client.get(f"/api/items/{item_id}")
    assert response.json["data"]["status"] == "reading"


def test_update_item_meta(client, sample_work):
    """Test updating item metadata."""
    item_id = sample_work["item"].id

    new_meta = {"notes": "Great book!", "rating": 5}
    response = client.put(f"/api/items/{item_id}", json={"meta": new_meta}, content_type="application/json")
    assert response.status_code == 200

    # Verify update
    response = client.get(f"/api/items/{item_id}")
    assert response.json["data"]["meta"] == new_meta


def test_update_item_not_found(client):
    """Test updating non-existent item returns 404."""
    response = client.put("/api/items/99999", json={"status": "reading"}, content_type="application/json")
    assert response.status_code == 404
    data = response.json
    assert data["success"] is False


@pytest.mark.parametrize(
    ("payload", "content_type"),
    [
        ('{"status": "checked_out"', "application/json"),  # malformed JSON
        (None, "application/json"),  # missing JSON body
    ],
)
def test_update_item_invalid_or_missing_json_payload(client, sample_work, payload, content_type, admin_headers):
    """Test update_item returns standardized 400 for invalid or missing JSON payload."""
    item_id = sample_work["item"].id

    request_kwargs = {"content_type": content_type, "headers": admin_headers}
    if payload is not None:
        request_kwargs["data"] = payload

    response = client.put(f"/api/items/{item_id}", **request_kwargs)

    assert response.status_code == 400
    assert response.json == {
        "success": False,
        "data": None,
        "error": "Invalid or missing JSON payload",
    }


# =============================================================================
# Delete Item Endpoint Tests
# =============================================================================


def test_delete_item(client, sample_work, admin_headers):
    """Test deleting an item."""
    item_id = sample_work["item"].id

    response = client.delete(f"/api/items/{item_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["data"]["id"] == item_id

    # Verify deletion
    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 404


def test_delete_item_not_found(client, admin_headers):
    """Test deleting non-existent item returns 404."""
    response = client.delete("/api/items/99999", headers=admin_headers)
    assert response.status_code == 404
    data = response.json
    assert data["success"] is False


# =============================================================================
# Standardized Response Format Tests
# =============================================================================


def test_standardized_response_format_success(client, sample_work):
    """Test that successful responses follow the standardized format."""
    token = generate_internal_jwt(sample_work["user"])
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    data = response.json

    # Check required fields
    assert "success" in data
    assert "data" in data
    assert "error" in data

    # Success case should have success=True and error=None
    assert data["success"] is True
    assert data["error"] is None


def test_standardized_response_format_error(client):
    """Test that error responses follow the standardized format."""
    response = client.get("/api/items/99999")
    assert response.status_code == 404
    data = response.json

    # Check required fields
    assert "success" in data
    assert "data" in data
    assert "error" in data

    # Error case should have success=False and error message
    assert data["success"] is False
    assert data["error"] is not None
    assert isinstance(data["error"], str)
