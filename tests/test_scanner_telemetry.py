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

"""Tests for scan telemetry recording, oversized barcode handling, and policy/intent separation."""

import uuid

from flask import Flask
from flask.testing import FlaskClient

from app.api.scanner import _record_scan_telemetry
from app.db.models import Item, Manifestation, ScanTelemetry, UserWorkIntent, db


def test_record_scan_telemetry_oversized_barcode(app: Flask) -> None:
    """Verifies that an oversized barcode is truncated and recorded with status='rejected_oversized'."""
    long_barcode = "A" * 200
    with app.app_context():
        _record_scan_telemetry(
            barcode=long_barcode,
            format_hint="book",
            provider="test_provider_oversized",
            status="success",
        )

        record = ScanTelemetry.query.filter_by(provider="test_provider_oversized", status="rejected_oversized").first()
        assert record is not None
        assert record.status == "rejected_oversized"
        assert len(record.barcode) <= 128
        assert record.barcode == f"{'A' * 120}...(200)"


def test_record_scan_telemetry_normal_barcode(app: Flask) -> None:
    """Verifies that a normal-length barcode (<= 128 chars) preserves original status and full value."""
    normal_barcode = "9780132350884"
    with app.app_context():
        _record_scan_telemetry(
            barcode=normal_barcode,
            format_hint="book",
            provider="test_provider_normal",
            status="success",
        )

        record = ScanTelemetry.query.filter_by(provider="test_provider_normal", barcode=normal_barcode).first()
        assert record is not None
        assert record.status == "success"
        assert record.barcode == normal_barcode


def test_scan_with_policy_inventory_only_creates_item(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning with policy='inventory' strictly mutates Item.collection_status and does not create UserWorkIntent."""
    payload = {
        "barcode": "9780131103627",
        "format": "book",
        "collection_status": "available",
        "policy": "inventory",
        "meta": {
            "title": "The C Programming Language",
            "author": "Brian W. Kernighan, Dennis M. Ritchie",
            "format": "book",
            "barcode": "9780131103627",
            "cover_url": "https://example.com/c.jpg",
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 201
    assert response.json is not None
    data = response.json.get("data", {})
    assert data.get("action") == "added_to_inventory"
    item_id = data.get("item_id")
    assert item_id is not None

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None
        assert item.collection_status == "available"

        manifestation = db.session.get(Manifestation, item.manifestation_id)
        assert manifestation is not None
        work_id = manifestation.expression.work_id

        # Verify no UserWorkIntent was created for this work
        intent = UserWorkIntent.query.filter_by(work_id=work_id).first()
        assert intent is None


def test_scan_with_policy_catalog_no_item_or_intent(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning with policy='catalog' registers manifestation metadata without creating Item or UserWorkIntent."""
    payload = {
        "barcode": "9780201616224",
        "format": "book",
        "policy": "catalog",
        "meta": {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt, David Thomas",
            "format": "book",
            "barcode": "9780201616224",
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 201
    assert response.json is not None
    data = response.json.get("data", {})
    assert data.get("action") == "cataloged"
    assert data.get("item_id") is None
    assert data.get("intent_id") is None

    manifestation_id = data.get("manifestation_id")
    with app.app_context():
        manifestation = db.session.get(Manifestation, manifestation_id)
        assert manifestation is not None

        items = Item.query.filter_by(manifestation_id=manifestation_id).all()
        assert len(items) == 0

        intents = UserWorkIntent.query.filter_by(work_id=manifestation.expression.work_id).all()
        assert len(intents) == 0


def test_scan_with_policy_catalog_only_no_item_or_intent(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning with policy='catalog_only' registers manifestation metadata without creating Item or UserWorkIntent."""
    unique_barcode = f"CATONLY{uuid.uuid4().hex[:8]}"
    payload = {
        "barcode": unique_barcode,
        "format": "book",
        "policy": "catalog_only",
        "meta": {
            "title": "Catalog Only Test Book",
            "author": "Catalog Author",
            "format": "book",
            "barcode": unique_barcode,
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 201
    assert response.json is not None
    data = response.json.get("data", {})
    assert data.get("action") == "cataloged"
    assert data.get("item_id") is None
    assert data.get("intent_id") is None

    manifestation_id = data.get("manifestation_id")
    with app.app_context():
        manifestation = db.session.get(Manifestation, manifestation_id)
        assert manifestation is not None

        items = Item.query.filter_by(manifestation_id=manifestation_id).all()
        assert len(items) == 0

        intents = UserWorkIntent.query.filter_by(work_id=manifestation.expression.work_id).all()
        assert len(intents) == 0


def test_scan_with_invalid_policy_fails(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning with an invalid policy string returns 400 validation error and makes no DB changes."""
    unique_barcode = f"INV{uuid.uuid4().hex[:8]}"
    payload = {
        "barcode": unique_barcode,
        "format": "book",
        "policy": "invalid_policy_mode",
        "meta": {
            "title": "Invalid Policy Test",
            "author": "Test Author",
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 400

    with app.app_context():
        manifestation = Manifestation.query.filter_by(barcode=unique_barcode).first()
        assert manifestation is None


def test_scan_with_policy_wishlist_only_creates_intent(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning with policy='wishlist' strictly creates UserWorkIntent and does not create Item."""
    unique_barcode = f"WISH{uuid.uuid4().hex[:8]}"
    payload = {
        "barcode": unique_barcode,
        "format": "book",
        "collection_status": "available",
        "policy": "wishlist",
        "meta": {
            "title": "Wishlist Only Test Book",
            "author": "Wishlist Author",
            "format": "book",
            "barcode": unique_barcode,
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 201
    assert response.json is not None
    data = response.json.get("data", {})
    assert data.get("action") == "added_to_wishlist"
    assert data.get("item_id") is None
    intent_id = data.get("intent_id")
    assert intent_id is not None

    manifestation_id = data.get("manifestation_id")
    with app.app_context():
        manifestation = db.session.get(Manifestation, manifestation_id)
        assert manifestation is not None

        items = Item.query.filter_by(manifestation_id=manifestation_id).all()
        assert len(items) == 0

        intent = db.session.get(UserWorkIntent, intent_id)
        assert intent is not None
        assert intent.work_id == manifestation.expression.work_id
        assert intent.status.startswith("want_to_")


def test_scan_omitted_policy_defaults_to_inventory(client: FlaskClient, normal_user_headers: dict[str, str], app: Flask) -> None:
    """Verifies scanning without an explicit policy defaults to inventory item creation."""
    unique_barcode = f"DEF{uuid.uuid4().hex[:8]}"
    payload = {
        "barcode": unique_barcode,
        "format": "book",
        "meta": {
            "title": "Default Policy Test Book",
            "author": "Default Author",
            "format": "book",
            "barcode": unique_barcode,
        },
    }

    response = client.post("/api/scan", json=payload, headers=normal_user_headers)
    assert response.status_code == 201
    assert response.json is not None
    data = response.json.get("data", {})
    assert data.get("action") == "added_to_inventory"
    item_id = data.get("item_id")
    assert item_id is not None

    manifestation_id = data.get("manifestation_id")
    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None
        assert item.collection_status == "available"

        manifestation = db.session.get(Manifestation, manifestation_id)
        assert manifestation is not None

        # Verify no UserWorkIntent was created
        intent = UserWorkIntent.query.filter_by(work_id=manifestation.expression.work_id).first()
        assert intent is None
