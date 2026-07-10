# tests/test_openapi.py
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

from app import create_app


@pytest.fixture
def app():
    # Setup test app specifically checking OpenAPI behavior constraints
    app = create_app(config_override={"TESTING": True, "APP_VERSION": "0.7.9"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_openapi_spec_generation(client):
    """Test that the OpenAPI spec accurately mounts, generates, and propagates the semantic schema."""
    response = client.get("/api/docs/openapi.json")

    assert response.status_code == 200
    assert response.is_json

    data = response.get_json()

    # Assert structural conformity
    assert "openapi" in data
    assert data["openapi"] == "3.0.3"

    # Assert semantic constraints
    assert "info" in data
    assert data["info"]["title"] == "iqoqo API"
    assert data["info"]["version"] == "0.7.9"

    # Assert operational bindings
    assert "paths" in data
    assert "/api/docs/openapi.json" in data["paths"], "Self-documenting route failed to inject into path schema."
