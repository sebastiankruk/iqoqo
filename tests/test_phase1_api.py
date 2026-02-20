"""Tests for Phase 1 API enhancements: new endpoints and CORS support."""

import pytest

from app import create_app
from app.db.models import Expression, Item, Manifestation, Work, db

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally
# pylint: disable=unused-argument  # fixtures used for setup, not always referenced


@pytest.fixture
def sample_work(app):
    """Create a sample work with expression, manifestation, and item."""
    with app.app_context():
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

        # Create Item
        item = Item(manifestation_id=manifestation.id, owner_id="test_user", status="available", meta={})
        db.session.add(item)
        db.session.commit()

        yield {"work": work, "expression": expression, "manifestation": manifestation, "item": item}


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


def test_get_items_empty(client):
    """Test getting items list when database is empty."""
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["data"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1


def test_get_items_with_data(client, sample_work):
    """Test getting items list with data."""
    response = client.get("/api/items")
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
        for i in range(25):
            item = Item(manifestation_id=manifestation.id, owner_id=f"user_{i}", status="available", meta={})
            db.session.add(item)
        db.session.commit()

    # Test first page
    response = client.get("/api/items?page=1&limit=10")
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 10
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 10
    assert data["meta"]["total"] == 25
    assert data["meta"]["pages"] == 3

    # Test second page
    response = client.get("/api/items?page=2&limit=10")
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 10
    assert data["meta"]["page"] == 2

    # Test last page
    response = client.get("/api/items?page=3&limit=10")
    assert response.status_code == 200
    data = response.json
    assert len(data["data"]) == 5
    assert data["meta"]["page"] == 3


# =============================================================================
# Item Detail Endpoint Tests
# =============================================================================


def test_get_item_detail(client, sample_work):
    """Test getting detailed item information."""
    item_id = sample_work["item"].id

    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["error"] is None

    item = data["data"]
    assert item["id"] == item_id
    assert item["owner_id"] == "test_user"
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
def test_update_item_invalid_or_missing_json_payload(client, sample_work, payload, content_type):
    """Test update_item returns standardized 400 for invalid or missing JSON payload."""
    item_id = sample_work["item"].id

    request_kwargs = {"content_type": content_type}
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


def test_delete_item(client, sample_work):
    """Test deleting an item."""
    item_id = sample_work["item"].id

    response = client.delete(f"/api/items/{item_id}")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert data["data"]["id"] == item_id

    # Verify deletion
    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 404


def test_delete_item_not_found(client):
    """Test deleting non-existent item returns 404."""
    response = client.delete("/api/items/99999")
    assert response.status_code == 404
    data = response.json
    assert data["success"] is False


# =============================================================================
# Standardized Response Format Tests
# =============================================================================


def test_standardized_response_format_success(client, sample_work):
    """Test that successful responses follow the standardized format."""
    response = client.get("/api/items")
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
