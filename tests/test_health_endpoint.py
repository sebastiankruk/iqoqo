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
"""Tests for the /api/health endpoint used by the native server-selector flow.

The mobile app calls GET /api/health to verify that a user-entered URL points
to a real iqoqo instance before persisting it.
"""
import pytest


def test_health_returns_200(client):
    """GET /api/health must return HTTP 200."""
    res = client.get("/api/health")
    assert res.status_code == 200


def test_health_response_is_json(client):
    """GET /api/health must return JSON."""
    res = client.get("/api/health")
    assert res.is_json


def test_health_contains_status_ok(client):
    """GET /api/health JSON body should include a positive status indicator."""
    res = client.get("/api/health")
    data = res.get_json()
    # Accept {"status": "ok"} or {"ok": true} — just verify something truthy.
    assert data.get("status") == "ok" or data.get("ok") is True or data.get("healthy") is True, (
        f"Unexpected health response body: {data}"
    )
