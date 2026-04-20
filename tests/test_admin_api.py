"""Tests for the admin API endpoints."""

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

# pylint: disable=redefined-outer-name  # pytest fixtures

import json
from io import BytesIO

import pytest

from app.core.data_manager import DataManager
from app.db.models import Expression, InstanceSettings, Item, Manifestation, Work


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


def test_admin_stats_empty(client, admin_headers):
    """Test /api/admin/stats with empty database."""
    response = client.get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 200

    data = response.json
    assert data["works"] == 0
    assert data["expressions"] == 0
    assert data["manifestations"] == 0
    assert data["items"] == 0


def test_admin_stats_with_data(app, client, admin_headers, sample_export_data):
    """Test /api/admin/stats with data in database."""
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    response = client.get("/api/admin/stats", headers=admin_headers)
    assert response.status_code == 200

    data = response.json
    assert data["works"] == 1
    assert data["expressions"] == 1
    assert data["manifestations"] == 1
    assert data["items"] == 1


def test_admin_export_empty(client, admin_headers):
    """Test /api/admin/export with empty database."""
    response = client.get("/api/admin/export", headers=admin_headers)
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


def test_admin_export_with_data(app, client, admin_headers, sample_export_data):
    """Test /api/admin/export with data in database."""
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    response = client.get("/api/admin/export", headers=admin_headers)
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["version"] == "1.0"
    assert len(data["works"]) == 1
    assert data["works"][0]["title"] == "1984"
    assert len(data["manifestations"]) == 1
    assert data["manifestations"][0]["isbn13"] == "9780451524935"


def test_admin_import_json_body(client, admin_headers, sample_export_data):
    """Test /api/admin/import with JSON in request body."""
    response = client.post("/api/admin/import", data=json.dumps(sample_export_data), content_type="application/json", headers=admin_headers)

    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert data["imported"]["works"] == 1
    assert data["imported"]["expressions"] == 1
    assert data["imported"]["manifestations"] == 1
    assert data["imported"]["items"] == 1


def test_admin_import_multipart_file(client, admin_headers, sample_export_data):
    """Test /api/admin/import with multipart file upload."""
    file_content = json.dumps(sample_export_data).encode("utf-8")

    response = client.post(
        "/api/admin/import",
        data={"file": (BytesIO(file_content), "export.json")},
        content_type="multipart/form-data",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert data["imported"]["works"] == 1


def test_admin_import_with_clear(app, client, admin_headers, sample_export_data):
    """Test /api/admin/import with clear_existing parameter."""
    # First import
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)
        assert Work.query.count() == 1

    # Import again with clear
    response = client.post(
        "/api/admin/import?clear_existing=true", data=json.dumps(sample_export_data), content_type="application/json", headers=admin_headers
    )

    assert response.status_code == 200

    # Should still have only 1 work (not 2)
    with app.app_context():
        assert Work.query.count() == 1


def test_admin_import_invalid_json(client, admin_headers):
    """Test /api/admin/import with invalid JSON."""
    response = client.post("/api/admin/import", data="not valid json", content_type="application/json", headers=admin_headers)

    # Flask returns 400 for JSON parsing errors
    assert response.status_code == 400


def test_admin_import_no_data(client, admin_headers):
    """Test /api/admin/import without data or file."""
    response = client.post("/api/admin/import", headers=admin_headers)

    assert response.status_code == 400
    assert "error" in response.json


def test_admin_clear_without_confirmation(client, admin_headers):
    """Test /api/admin/clear without confirmation."""
    response = client.delete("/api/admin/clear", data=json.dumps({}), content_type="application/json", headers=admin_headers)
    assert "error" in response.json
    assert "confirm" in response.json["error"].lower()


def test_admin_clear_with_confirmation(app, client, admin_headers, sample_export_data):
    """Test /api/admin/clear with proper confirmation."""
    # Import some data first
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)
        assert Work.query.count() == 1

    # Clear with confirmation
    response = client.delete("/api/admin/clear", data=json.dumps({"confirm": True}), content_type="application/json", headers=admin_headers)

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


def test_admin_clear_with_false_confirmation(client, admin_headers):
    """Test /api/admin/clear with confirm=false."""
    response = client.delete(
        "/api/admin/clear", data=json.dumps({"confirm": False}), content_type="application/json", headers=admin_headers
    )

    assert response.status_code == 400
    assert "error" in response.json


@pytest.mark.parametrize(
    ("payload", "content_type"),
    [
        ('{"confirm": true', "application/json"),  # malformed JSON
        (None, "application/json"),  # missing JSON body
    ],
)
def test_admin_clear_invalid_or_missing_json_payload(client, admin_headers, payload, content_type):
    """Test /api/admin/clear returns standardized 400 for invalid or missing JSON payload."""
    request_kwargs = {"content_type": content_type, "headers": admin_headers}
    if payload is not None:
        request_kwargs["data"] = payload

    response = client.delete("/api/admin/clear", **request_kwargs)

    assert response.status_code == 400
    assert response.json == {
        "success": False,
        "data": None,
        "error": "Invalid or missing JSON payload",
    }


def test_full_export_import_cycle(app, client, admin_headers, sample_export_data):
    """Test complete export-import-export cycle."""
    # 1. Import initial data
    with app.app_context():
        DataManager.import_data(sample_export_data, clear_existing=False)

    # 2. Export via API
    export_response = client.get("/api/admin/export", headers=admin_headers)
    assert export_response.status_code == 200
    exported_data = json.loads(export_response.data)

    # 3. Clear database
    clear_response = client.delete(
        "/api/admin/clear", data=json.dumps({"confirm": True}), content_type="application/json", headers=admin_headers
    )
    assert clear_response.status_code == 200

    # 4. Verify empty
    with app.app_context():
        assert Work.query.count() == 0

    # 5. Re-import the exported data
    import_response = client.post(
        "/api/admin/import", data=json.dumps(exported_data), content_type="application/json", headers=admin_headers
    )
    assert import_response.status_code == 200

    # 6. Verify data is back
    with app.app_context():
        assert Work.query.count() == 1
        work = Work.query.first()
        assert work.title == "1984"


def test_admin_import_handles_exceptions(client, admin_headers):
    """Test that import endpoint handles database errors gracefully."""
    # Missing required fields
    invalid_data = {
        "version": "1.0",
        "works": [{"id": 1}],  # Missing required 'title' field
        "expressions": [],
        "manifestations": [],
        "items": [],
    }

    response = client.post("/api/admin/import", data=json.dumps(invalid_data), content_type="application/json", headers=admin_headers)

    # Should return error, not crash
    assert response.status_code in [400, 500]
    assert "error" in response.json


# Additional admin settings RBAC tests
def test_admin_settings_access_denied(client):
    """Ensure unauthenticated or normal users get 403 Forbidden."""
    # No auth headers provided
    res = client.get("/api/v1/admin/settings")
    assert res.status_code in [401, 403]


def test_admin_settings_access_granted(client, admin_headers):
    """Ensure admins can fetch settings."""
    res = client.get("/api/v1/admin/settings", headers=admin_headers)
    assert res.status_code == 200
    assert "success" in res.json


def test_admin_settings_update(client, app, admin_headers):
    """Ensure admins can update key-value settings."""
    payload = {
        "instance_name": "Test Federation Library",
        "amazon_affiliate_id": "test-20",
    }
    res = client.put("/api/v1/admin/settings", json=payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["data"]["amazon_affiliate_id"] == "test-20"

    with app.app_context():
        setting = InstanceSettings.query.filter_by(key="instance_name").first()
        assert setting is not None
        assert setting.value == "Test Federation Library"
