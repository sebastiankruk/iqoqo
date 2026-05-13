"""
Security audit tests for the Items API based on RBAC rules.
Validates the @require_permission decorators for new intents.
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


def test_add_to_library_requires_write_permission(client, guest_user_headers):
    """Ensure GUEST roles receive 403 Forbidden when trying to add physical items."""
    payload = {"Title": "Dune", "Format": "BOOK"}

    response = client.post("/api/items/manual", data=json.dumps(payload), headers=guest_user_headers, content_type="application/json")

    assert response.status_code == 403
    data = response.get_json()
    assert "Forbidden" in data.get("error", "")
    assert data.get("missing_permission") == "write:item"


def test_add_item_requires_write_permission_scan(client, guest_user_headers):
    """Ensure GUEST roles receive 403 Forbidden when trying to scan and add items."""
    payload = {"barcode": "9780441172719", "collection_status": "available"}

    response = client.post("/api/scan", data=json.dumps(payload), headers=guest_user_headers, content_type="application/json")

    assert response.status_code == 403
    data = response.get_json()
    assert data.get("missing_permission") == "write:item"
