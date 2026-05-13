"""
Tests for explicit Pydantic payload validation on the Items API.
Ensures we strictly return {"error": "...", "code": 400} on malformed requests.
"""

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json

import pytest


def test_add_item_missing_required_fields(client, normal_user_headers):
    """Ensure POST /api/items/manual rejects payloads missing required FRBR attributes."""
    # Note: /api/items/<isbn> (add_item) has optional everything in ItemCreateSchema
    # but /api/items/manual (add_item_manual) requires Title.
    payload = {
        "status": "want_to_read"
        # Missing required 'Title'
    }

    response = client.post("/api/items/manual", data=json.dumps(payload), headers=normal_user_headers, content_type="application/json")

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "code" in data
    assert data["code"] == 400
    assert "field required" in data["error"].lower()


def test_add_item_invalid_data_types(client, normal_user_headers):
    """Ensure boundary limits and strict type checking block malformed JSON."""
    payload = {"Title": 12345, "Format": "BOOK", "collection_status": "UNKNOWN_ENUM_VALUE"}  # Should be string

    response = client.post("/api/items/manual", data=json.dumps(payload), headers=normal_user_headers, content_type="application/json")

    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "error" in data


def test_add_item_malformed_json(client, normal_user_headers):
    """Ensure the API catches completely broken JSON gracefully."""
    response = client.post("/api/items/manual", data="{ bad_json: true ", headers=normal_user_headers, content_type="application/json")

    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == 400
    assert "invalid or missing json payload" in data["error"].lower()
