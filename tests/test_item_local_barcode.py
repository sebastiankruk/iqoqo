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
"""Tests for Item exemplar-level local_barcode identification."""

import json

import pytest

from app.db.models import Expression, Item, Manifestation, Work, db


@pytest.fixture
def sample_manifestation(app):
    """Seed an isolated FRBR hierarchy with Manifestation and ISBN."""
    with app.app_context():
        work = Work(title="The Art of Unix Programming", meta={"authors": ["Eric S. Raymond"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780131429017",
            meta={"title": "The Art of Unix Programming"},
            publisher="Addison-Wesley",
        )
        db.session.add(manif)
        db.session.commit()
        return manif.id


def test_item_to_dict_includes_local_barcode(app, sample_manifestation):
    """Verify Item.to_dict() serializes local_barcode."""
    import uuid

    with app.app_context():
        item = Item(
            manifestation_id=sample_manifestation,
            owner_id=uuid.uuid4(),
            local_barcode="LIB-INV-00123",
            status="want_to_read",
            collection_status="available",
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d["local_barcode"] == "LIB-INV-00123"
        assert d["manifestation_id"] == sample_manifestation


def test_create_item_with_local_barcode(client, normal_user_headers, sample_manifestation):
    """Scenario: Setting local barcode during item creation via POST /api/items."""
    payload = {
        "manifestation_id": sample_manifestation,
        "local_barcode": "SHELF-TAG-789",
        "status": "want_to_read",
        "collection_status": "available",
    }

    res = client.post(
        "/api/items",
        data=json.dumps(payload),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    item_id = data["data"]["item_id"]
    assert data["data"]["local_barcode"] == "SHELF-TAG-789"

    # Detail GET verification
    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert get_res.status_code == 200
    item_detail = get_res.get_json()["data"]
    assert item_detail["local_barcode"] == "SHELF-TAG-789"
    assert item_detail["isbn"] == "9780131429017"


def test_add_item_by_manifestation_with_local_barcode(client, normal_user_headers, sample_manifestation):
    """Creating item via POST /api/manifestations/<id>/add persists local_barcode."""
    payload = {
        "local_barcode": "BARCODE-MFN-101",
        "status": "want_to_read",
        "collection_status": "available",
    }

    res = client.post(
        f"/api/manifestations/{sample_manifestation}/add",
        data=json.dumps(payload),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["local_barcode"] == "BARCODE-MFN-101"

    item_id = data["data"]["item_id"]
    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["local_barcode"] == "BARCODE-MFN-101"


def test_update_item_local_barcode(client, normal_user_headers, sample_manifestation):
    """Scenario: Updating item local barcode via PUT /api/items/<id>."""
    create_res = client.post(
        "/api/items",
        data=json.dumps({"manifestation_id": sample_manifestation, "local_barcode": "OLD-TAG"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201
    item_id = create_res.get_json()["data"]["item_id"]

    # Update barcode
    update_res = client.put(
        f"/api/items/{item_id}",
        data=json.dumps({"local_barcode": "NEW-TAG-456"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert update_res.status_code == 200
    assert update_res.get_json()["data"]["local_barcode"] == "NEW-TAG-456"

    # Verify retrieval
    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert get_res.get_json()["data"]["local_barcode"] == "NEW-TAG-456"


def test_clear_item_local_barcode(client, normal_user_headers, sample_manifestation):
    """Scenario: Clearing item local barcode via PUT /api/items/<id> with null or empty."""
    create_res = client.post(
        "/api/items",
        data=json.dumps({"manifestation_id": sample_manifestation, "local_barcode": "TAG-TO-CLEAR"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201
    item_id = create_res.get_json()["data"]["item_id"]

    # Clear with empty string
    update_res = client.put(
        f"/api/items/{item_id}",
        data=json.dumps({"local_barcode": ""}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert update_res.status_code == 200

    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert get_res.get_json()["data"]["local_barcode"] is None


def test_ontological_distinction_manifestation_isbn_and_item_barcode(client, normal_user_headers, sample_manifestation):
    """Requirement: Ontological Distinction from Manifestation Identifiers."""
    create_res = client.post(
        "/api/items",
        data=json.dumps({"manifestation_id": sample_manifestation, "local_barcode": "LOCAL-ITEM-999"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201
    item_id = create_res.get_json()["data"]["item_id"]

    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    detail = get_res.get_json()["data"]

    # Manifestation level has ISBN
    assert detail["isbn"] == "9780131429017"
    # Item level has local_barcode
    assert detail["local_barcode"] == "LOCAL-ITEM-999"


def test_update_item_condition_persists(client, normal_user_headers, sample_manifestation):
    """Verify PUT /api/items/<id> persists condition on Item."""
    create_res = client.post(
        "/api/items",
        data=json.dumps({"manifestation_id": sample_manifestation, "status": "want_to_read"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201
    item_id = create_res.get_json()["data"]["item_id"]

    update_res = client.put(
        f"/api/items/{item_id}",
        data=json.dumps({"condition": "near_mint"}),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert update_res.status_code == 200

    get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["condition"] == "near_mint"


def test_create_item_unowned_collection_rejected(client, normal_user_headers, sample_manifestation):
    """Verify POST /api/items with unowned or non-existent collection_id is rejected."""
    res = client.post(
        "/api/items",
        data=json.dumps(
            {
                "manifestation_id": sample_manifestation,
                "collection_id": 999999,
            }
        ),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert res.status_code == 404
    assert "Collection not found" in res.get_json()["error"]


def test_add_item_by_manifestation_unowned_collection_rejected(client, normal_user_headers, sample_manifestation):
    """Verify POST /api/manifestations/<id>/add with unowned collection_id is rejected."""
    res = client.post(
        f"/api/manifestations/{sample_manifestation}/add",
        data=json.dumps(
            {
                "collection_id": 999999,
            }
        ),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert res.status_code == 404
    assert "Collection not found" in res.get_json()["error"]


def test_lookup_by_local_barcode_resolves_manifestation(client, normal_user_headers, sample_manifestation):
    """Verify GET /api/lookup/<barcode> resolves locally via Item.local_barcode."""
    local_code = "LOCAL-STICKER-998877"
    create_res = client.post(
        "/api/items",
        data=json.dumps(
            {
                "manifestation_id": sample_manifestation,
                "local_barcode": local_code,
                "status": "want_to_read",
            }
        ),
        headers=normal_user_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201

    lookup_res = client.get(f"/api/lookup/{local_code}", headers=normal_user_headers)
    assert lookup_res.status_code == 200
    data = lookup_res.get_json()
    assert data["success"] is True
    assert data["data"]["local_barcode"] == local_code
    assert data["data"]["manifestation_id"] == sample_manifestation
