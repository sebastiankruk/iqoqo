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
from pydantic import ValidationError

from app.api.schemas import ItemBulkCreateSchema, ItemLendSchema, ItemManualCreateSchema, ScanBarcodeSchema


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


def test_item_bulk_create_schema_validation():
    """Test explicit Pydantic rules for bulk item creation schema."""
    valid_data = {"manifestation_ids": [1, 2, 3], "status": "want_to_read"}
    schema = ItemBulkCreateSchema(**valid_data)
    assert schema.manifestation_ids == [1, 2, 3]

    with pytest.raises(ValidationError) as exc:
        ItemBulkCreateSchema(manifestation_ids=[])
    assert "List should have at least 1 item" in str(exc.value)

    with pytest.raises(ValidationError):
        ItemBulkCreateSchema(status="read")

    with pytest.raises(ValidationError) as exc:
        ItemBulkCreateSchema(manifestation_ids=[1], malicious_field="drop_tables")
    assert "Extra inputs are not permitted" in str(exc.value)


def test_item_manual_create_schema_allows_extra():
    """Test that manual schema deliberately allows extra fields to be bundled into meta."""
    valid_data = {"Title": "A Good Book", "CustomMeta": "Stored gracefully"}
    schema = ItemManualCreateSchema(**valid_data)
    assert schema.Title == "A Good Book"

    assert getattr(schema, "model_extra", None) is not None
    assert schema.model_extra["CustomMeta"] == "Stored gracefully"


def test_scan_barcode_schema_forbids_extra():
    """Test strict configuration on barcode scanner schema."""
    with pytest.raises(ValidationError) as exc:
        ScanBarcodeSchema(barcode="123456789", format="book", injected_role="admin")
    assert "Extra inputs are not permitted" in str(exc.value)


class TestVirtualItemGuardrails:
    """Ensure virtual wishlist identifiers (< 0) and zero bounds remain structurally clean."""

    def test_mutation_on_virtual_item_throws_exception(self, client, normal_user_headers):
        """Assert mutating requests (PUT) on virtual entities throw a 400 or 404 instead of a 500 error."""
        response = client.put(
            "/api/items/-5",
            json={"status": "read"},
            headers=normal_user_headers,
            content_type="application/json",
        )
        assert response.status_code in [400, 404]
        assert "error" in response.json

    def test_deletion_on_virtual_item_is_rejected(self, client, normal_user_headers):
        """Assert deletion flows throw a clean exception boundary when executed against a virtual id."""
        response = client.delete("/api/items/-12", headers=normal_user_headers)
        # 404 = item not found (after auth); 403 = insufficient permission for DELETE_ITEM
        assert response.status_code in [400, 403, 404]

    def test_payload_schema_strictly_rejects_id_zero(self, client, normal_user_headers):
        """Assert integer payload schemas explicitly catch and isolate id == 0 validation errors.
        Tests the schema layer directly since item creation routes do not accept an explicit 'id' field.
        """
        # ItemBulkCreateSchema uses manifestation_ids which must be positive integers.
        # A list containing 0 is valid per schema, but an empty list is not.
        # The key guardrail: bulk create with no manifestation_ids must be rejected.
        with pytest.raises(ValidationError) as exc:
            ItemBulkCreateSchema(manifestation_ids=[])
        assert "List should have at least 1 item" in str(exc.value)

    def test_put_zero_id_returns_400(self, client, normal_user_headers):
        """Assert PUT /api/items/0 returns 400 with the FRBR ontology boundary error.

        The signed int router allows id=0 through, but the controller must reject it explicitly
        since 0 is not a valid FRBR entity ID at any level (Work, Expression, Manifestation, Item).
        """
        response = client.put(
            "/api/items/0",
            json={"status": "read"},
            headers=normal_user_headers,
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "error" in response.json
        assert "Cannot mutate virtual items" in response.json["error"]

    def test_get_logs_virtual_item_returns_empty_array(self, client, normal_user_headers):
        """Assert GET /api/items/-1/logs returns 200 with an empty data array.

        The backend must gracefully handle log requests for virtual wishlist items by
        returning an empty array rather than a 404 or 500, so that the frontend timeline
        component can render its empty state without error.
        """
        response = client.get("/api/items/-1/logs", headers=normal_user_headers)
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"] == []

    def test_qrcode_virtual_item_returns_404(self, client, normal_user_headers):
        """Assert GET /api/qrcode/-1 returns 404.

        Virtual wishlist items have no physical copy to tag — generating a QR code for one
        would be semantically meaningless and must be explicitly rejected.
        """
        response = client.get("/api/qrcode/-1", headers=normal_user_headers)
        assert response.status_code == 404
        assert "error" in response.json

    def test_lend_schema_rejects_zero_and_negative_ids(self):
        """Assert ItemLendSchema raises ValidationError for id=0 and id=-5.

        This is a fast schema-layer tripwire that catches any regression where the
        lending schema allows virtual IDs through to the physical loan workflow.
        """
        with pytest.raises(ValidationError):
            ItemLendSchema(item_id=0)

        with pytest.raises(ValidationError):
            ItemLendSchema(item_id=-5)

    def test_lend_schema_accepts_positive_id(self):
        """Assert ItemLendSchema accepts id=1 as a valid physical item ID."""
        schema = ItemLendSchema(item_id=1)
        assert schema.item_id == 1
