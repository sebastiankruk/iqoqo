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
"""Tests for the /api/health endpoint used by mobile ServerSelector."""

from flask.testing import FlaskClient


def test_health_endpoint_success(client: FlaskClient) -> None:
    """Test that /api/health returns 200 OK with expected status and service metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "iqoqo-api"
    assert "version" in data
    assert data["api_version"] == "v1"


def test_health_endpoint_drift_unauthorized(client: FlaskClient) -> None:
    """Test that /api/health?check_drift=1 rejects unauthenticated requests."""
    response = client.get("/api/health?check_drift=1")
    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data
