"""Tests for the admin API endpoints."""

import json
from io import BytesIO

import pytest

from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, Work


@pytest.fixture
def sample_export_data():
    """Sample data in export format."""
    return {
        "version": "1.0",
        "exported_at": "2026-01-30T12:00:00",
        "works": [{"id": 1, "title": "1984", "form": "novel", "date": "1949"}],
        "expressions": [{"id": 1, "work_id": 1, "language": "en", "expression_type": "text"}],
        "manifestations": [
            {
                "id": 1,
                "expression_id": 1,
                "isbn13": "9780451524935",
                "title": "1984",
                "publisher": "Signet Classic",
                "year": 1950,
            }
        ],
        "items": [{"id": 1, "manifestation_id": 1, "condition": "good"}],
    }


def test_admin_stats_empty(client):
    """Test /api/admin/stats with empty database."""
    response = client.get("/api/admin/stats")
    assert response.status_code == 200

    data = response.json
    assert data["works"] == 0
    assert data["expressions"] == 0
    assert data["manifestations"] == 0
    assert data["items"] == 0


def test_admin_stats_with_data(app, client, sample_export_data):
    """Test /api/admin/stats with data in database."""
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    response = client.get("/api/admin/stats")
    assert response.status_code == 200

    data = response.json
    assert data["works"] == 1
    assert data["expressions"] == 1
    assert data["manifestations"] == 1
    assert data["items"] == 1


def test_admin_export_empty(client):
    """Test /api/admin/export with empty database."""
    response = client.get("/api/admin/export")
    assert response.status_code == 200
    assert response.content_type == "application/json"

    # Check the attachment header
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers["Content-Disposition"]
    assert "iqoqo_export_" in response.headers["Content-Disposition"]

    data = json.loads(response.data)
    assert data["version"] == "1.0"
    assert data["works"] == []
    assert data["expressions"] == []
    assert data["manifestations"] == []
    assert data["items"] == []


def test_admin_export_with_data(app, client, sample_export_data):
    """Test /api/admin/export with data in database."""
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    response = client.get("/api/admin/export")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["version"] == "1.0"
    assert len(data["works"]) == 1
    assert data["works"][0]["title"] == "1984"
    assert len(data["manifestations"]) == 1
    assert data["manifestations"][0]["isbn13"] == "9780451524935"


def test_admin_import_json_body(client, sample_export_data):
    """Test /api/admin/import with JSON in request body."""
    response = client.post("/api/admin/import", data=json.dumps(sample_export_data), content_type="application/json")

    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert data["imported"]["works"] == 1
    assert data["imported"]["expressions"] == 1
    assert data["imported"]["manifestations"] == 1
    assert data["imported"]["items"] == 1


def test_admin_import_multipart_file(client, sample_export_data):
    """Test /api/admin/import with multipart file upload."""
    file_content = json.dumps(sample_export_data).encode("utf-8")

    response = client.post(
        "/api/admin/import", data={"file": (BytesIO(file_content), "export.json")}, content_type="multipart/form-data"
    )

    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert data["imported"]["works"] == 1


def test_admin_import_with_clear(app, client, sample_export_data):
    """Test /api/admin/import with clear_existing parameter."""
    # First import
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)
        assert Work.query.count() == 1

    # Import again with clear
    response = client.post(
        "/api/admin/import?clear_existing=true", data=json.dumps(sample_export_data), content_type="application/json"
    )

    assert response.status_code == 200

    # Should still have only 1 work (not 2)
    with app.app_context():
        assert Work.query.count() == 1


def test_admin_import_invalid_json(client):
    """Test /api/admin/import with invalid JSON."""
    response = client.post("/api/admin/import", data="not valid json", content_type="application/json")

    # Flask returns 500 for JSON parsing errors
    assert response.status_code == 500
    assert "error" in response.json


def test_admin_import_no_data(client):
    """Test /api/admin/import without data or file."""
    response = client.post("/api/admin/import")

    assert response.status_code == 400
    assert "error" in response.json


def test_admin_clear_without_confirmation(client):
    """Test /api/admin/clear without confirmation."""
    response = client.delete("/api/admin/clear", data=json.dumps({}), content_type="application/json")
    assert "error" in response.json
    assert "confirm" in response.json["error"].lower()


def test_admin_clear_with_confirmation(app, client, sample_export_data):
    """Test /api/admin/clear with proper confirmation."""
    # Import some data first
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)
        assert Work.query.count() == 1

    # Clear with confirmation
    response = client.delete("/api/admin/clear", data=json.dumps({"confirm": True}), content_type="application/json")

    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert "cleared" in data["message"].lower()

    # Verify data is gone
    with app.app_context():
        assert Work.query.count() == 0
        assert Expression.query.count() == 0
        assert Manifestation.query.count() == 0
        assert Item.query.count() == 0


def test_admin_clear_with_false_confirmation(client):
    """Test /api/admin/clear with confirm=false."""
    response = client.delete("/api/admin/clear", data=json.dumps({"confirm": False}), content_type="application/json")

    assert response.status_code == 400
    assert "error" in response.json


def test_full_export_import_cycle(app, client, sample_export_data):
    """Test complete export-import-export cycle."""
    # 1. Import initial data
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    # 2. Export via API
    export_response = client.get("/api/admin/export")
    assert export_response.status_code == 200
    exported_data = json.loads(export_response.data)

    # 3. Clear database
    clear_response = client.delete(
        "/api/admin/clear", data=json.dumps({"confirm": True}), content_type="application/json"
    )
    assert clear_response.status_code == 200

    # 4. Verify empty
    with app.app_context():
        assert Work.query.count() == 0

    # 5. Re-import the exported data
    import_response = client.post("/api/admin/import", data=json.dumps(exported_data), content_type="application/json")
    assert import_response.status_code == 200

    # 6. Verify data is back
    with app.app_context():
        assert Work.query.count() == 1
        work = Work.query.first()
        assert work.title == "1984"


def test_admin_import_handles_exceptions(client):
    """Test that import endpoint handles database errors gracefully."""
    # Missing required fields
    invalid_data = {
        "version": "1.0",
        "works": [{"id": 1}],  # Missing required 'title' field
        "expressions": [],
        "manifestations": [],
        "items": [],
    }

    response = client.post("/api/admin/import", data=json.dumps(invalid_data), content_type="application/json")

    # Should return error, not crash
    assert response.status_code in [400, 500]
    assert "error" in response.json
