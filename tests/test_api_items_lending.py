# tests/test_api_items_lending.py
"""Tests for strict borrower details requirements when items are lent out."""

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

import pytest

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def sample_manifestation(app):
    """Create a sample manifestation to link items against."""
    with app.app_context():
        w = Work(title="Lending Rules Test")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, isbn13="1234567890123")
        db.session.add(m)
        db.session.commit()
        return m.id


@pytest.fixture
def sample_item(app, sample_manifestation, normal_user_headers):
    """Create a sample item owned by the test user."""
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()
        item = Item(manifestation_id=sample_manifestation, owner_id=user.id, status="want_to_read", collection_status="available")
        db.session.add(item)
        db.session.commit()
        return item.id


def test_update_item_lent_with_name_success(client, sample_item, normal_user_headers, app):
    """Verify item update to 'lent' succeeds when a string borrower name is provided."""
    payload = {"collection_status": "lent", "lent_to_name": "Caveman Friend"}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    with app.app_context():
        item = db.session.get(Item, sample_item)
        assert item.collection_status == "lent"
        assert item.lent_to_name == "Caveman Friend"
        assert item.lent_to_user_id is None


def test_update_item_lent_with_user_id_success(client, sample_item, normal_user_headers, app):
    """Verify item update to 'lent' succeeds when a borrower user ID is provided."""
    with app.app_context():
        borrower = User(email="borrower@iqoqo.local", display_name="Borrower Caveman")
        db.session.add(borrower)
        db.session.commit()
        borrower_id = str(borrower.id)

    payload = {"collection_status": "lent", "lent_to_user_id": borrower_id}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    with app.app_context():
        item = db.session.get(Item, sample_item)
        assert item.collection_status == "lent"
        assert str(item.lent_to_user_id) == borrower_id
        assert item.lent_to_name is None


def test_update_item_lent_missing_borrower_fails(client, sample_item, normal_user_headers):
    """Verify updating collection_status to 'lent' fails with 400 if no borrower info is given."""
    payload = {"collection_status": "lent"}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 400
    assert "error" in response.json
    assert "require" in response.json["error"]


def test_update_item_lent_empty_name_fails(client, sample_item, normal_user_headers):
    """Verify updating collection_status to 'lent' fails with 400 if name is empty string."""
    payload = {"collection_status": "lent", "lent_to_name": "   "}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 400
    assert "error" in response.json


def test_add_item_lent_with_name_success(client, sample_manifestation, normal_user_headers, app):
    """Verify creating a lent item via POST /api/item/<isbn> succeeds with borrower name."""
    payload = {"collection_status": "lent", "lent_to_name": "Caveman Bob"}
    response = client.post("/api/item/1234567890123", json=payload, headers=normal_user_headers)
    assert response.status_code == 200
    item_id = response.json["data"]["item_id"]

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.collection_status == "lent"
        assert item.lent_to_name == "Caveman Bob"


def test_add_item_lent_missing_borrower_fails(client, sample_manifestation, normal_user_headers):
    """Verify creating a lent item via POST /api/item/<isbn> fails if borrower is missing."""
    payload = {"collection_status": "lent"}
    response = client.post("/api/item/1234567890123", json=payload, headers=normal_user_headers)
    assert response.status_code == 400
    assert "error" in response.json


def test_transition_away_from_lent_clears_borrower(client, sample_item, normal_user_headers, app):
    """Verify transition from 'lent' to 'available' auto-clears borrower details."""
    # First, make it lent
    payload = {"collection_status": "lent", "lent_to_name": "Caveman Borrower"}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 200

    # Transition to available
    payload = {"collection_status": "available"}
    response = client.put(f"/api/items/{sample_item}", json=payload, headers=normal_user_headers)
    assert response.status_code == 200

    with app.app_context():
        item = db.session.get(Item, sample_item)
        assert item.collection_status == "available"
        assert item.lent_to_name is None
        assert item.lent_to_user_id is None


def test_reset_lending_test_state_outside_testing_mode_returns_403(client, app):
    """Ensure POST /api/lending/test/reset returns 403 outside of testing mode."""
    orig_testing = app.config.get("TESTING")
    try:
        app.config["TESTING"] = False
        res = client.post("/api/lending/test/reset")
        assert res.status_code == 403
        assert res.json["error"] == "Forbidden"
    finally:
        app.config["TESTING"] = orig_testing


def test_reset_lending_test_state_production_env_returns_403(client, app, monkeypatch):
    """Ensure POST /api/lending/test/reset is strictly blocked in production even if TESTING is True."""
    monkeypatch.setenv("FLASK_ENV", "production")
    res = client.post("/api/lending/test/reset")
    assert res.status_code == 403
    assert res.json["error"] == "Forbidden"


def test_reset_lending_test_state_allowed_in_test_mode(client, app):
    """Ensure POST /api/lending/test/reset succeeds in testing mode."""
    orig_testing = app.config.get("TESTING")
    try:
        app.config["TESTING"] = True
        res = client.post("/api/lending/test/reset")
        assert res.status_code == 200
        assert res.json["success"] is True
    finally:
        app.config["TESTING"] = orig_testing
