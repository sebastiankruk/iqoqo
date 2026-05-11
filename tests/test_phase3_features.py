"""Tests for Phase 3 DevOps and Maintenance features."""

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

import io

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, ImageScan, InstanceSettings, Manifestation, Permission, Role, User, Work, db


@pytest.fixture
def sample_manifestation(app):
    """Create a sample manifestation for testing."""
    with app.app_context():
        work = Work(title="Test Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, publisher="Test Pub")
        db.session.add(mani)
        db.session.commit()
        return mani.id


def test_maintenance_mode_can_be_set_by_admin(client, admin_headers, app):
    """Test that admin can toggle maintenance mode."""
    response = client.put("/api/v1/admin/settings", json={"MAINTENANCE_MODE": "true"}, headers=admin_headers)
    assert response.status_code == 200

    with app.app_context():
        setting = InstanceSettings.query.filter_by(key="MAINTENANCE_MODE").first()
        assert setting is not None
        assert setting.value == "true"


def test_maintenance_mode_readable_via_get(client, admin_headers):
    """Test that maintenance mode is visible in instance settings."""
    # First set it
    client.put("/api/v1/admin/settings", json={"MAINTENANCE_MODE": "false"}, headers=admin_headers)

    response = client.get("/api/v1/admin/settings?category=internal", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "MAINTENANCE_MODE" in data["data"]
    assert data["data"]["MAINTENANCE_MODE"]["value"] == "false"


def test_upload_manifestation_image_custom_source(client, admin_headers, sample_manifestation, app):
    """Test that image upload respects custom source parameter."""
    # 1x1 Transparent PNG
    png_binary = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    data = {"image": (io.BytesIO(png_binary), "test.png"), "label": "cover", "source": "scanner_auto_fallback"}
    response = client.post(
        f"/api/manifestations/{sample_manifestation}/images", data=data, content_type="multipart/form-data", headers=admin_headers
    )
    assert response.status_code == 201

    with app.app_context():
        scan = ImageScan.query.filter_by(manifestation_id=sample_manifestation).order_by(ImageScan.id.desc()).first()
        assert scan is not None
        assert scan.source == "scanner_auto_fallback"


def test_upload_manifestation_image_default_source(client, admin_headers, sample_manifestation, app):
    """Test that image upload defaults to user_upload."""
    # 1x1 Transparent PNG
    png_binary = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    data = {"image": (io.BytesIO(png_binary), "test.png"), "label": "gallery"}
    response = client.post(
        f"/api/manifestations/{sample_manifestation}/images", data=data, content_type="multipart/form-data", headers=admin_headers
    )
    assert response.status_code == 201

    with app.app_context():
        scan = ImageScan.query.filter_by(manifestation_id=sample_manifestation).order_by(ImageScan.id.desc()).first()
        assert scan is not None
        assert scan.source == "user_upload"
