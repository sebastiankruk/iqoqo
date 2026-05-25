# tests/test_api_items_qrcode.py
"""Tests for the /api/qrcode/<item_id> endpoint."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#

import pytest

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def seeded_item(app):
    """Seed the database with an owner, manifestation, and item."""
    with app.app_context():
        # Owner user
        owner = User(email="qrcode_owner@iqoqo.local", display_name="QR Owner")
        db.session.add(owner)
        db.session.flush()

        # Non-owner user
        other_user = User(email="qrcode_other@iqoqo.local", display_name="QR Other")
        db.session.add(other_user)
        db.session.flush()

        w = Work(title="QR Book")
        db.session.add(w)
        db.session.flush()

        e = Expression(work_id=w.id, content_type=MediaCategory.TEXT)
        db.session.add(e)
        db.session.flush()

        m = Manifestation(expression_id=e.id, meta={"format": MediaFormat.BOOK})
        db.session.add(m)
        db.session.flush()

        item = Item(manifestation_id=m.id, owner_id=owner.id, status="available")
        db.session.add(item)
        db.session.flush()

        db.session.commit()

        return {
            "owner_id": owner.id,
            "other_id": other_user.id,
            "item_id": item.id,
        }


def test_get_qrcode_png_success(client, seeded_item, app) -> None:
    """Test generating a PNG QR code successfully for item owner."""
    from app.api.auth import generate_internal_jwt

    user_id = seeded_item["owner_id"]
    item_id = seeded_item["item_id"]

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/qrcode/{item_id}", headers=headers)
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert len(response.data) > 0


def test_get_qrcode_svg_success(client, seeded_item, app) -> None:
    """Test generating an SVG QR code successfully for item owner."""
    from app.api.auth import generate_internal_jwt

    user_id = seeded_item["owner_id"]
    item_id = seeded_item["item_id"]

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/qrcode/{item_id}?format=svg", headers=headers)
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert b"<svg" in response.data


def test_get_qrcode_unauthorized(client, seeded_item) -> None:
    """Test generating QR code without authentication."""
    item_id = seeded_item["item_id"]
    response = client.get(f"/api/qrcode/{item_id}")
    assert response.status_code == 401


def test_get_qrcode_forbidden_bola(client, seeded_item, app) -> None:
    """Test non-owner is blocked with BOLA-compliant 404."""
    from app.api.auth import generate_internal_jwt

    user_id = seeded_item["other_id"]
    item_id = seeded_item["item_id"]

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/api/qrcode/{item_id}", headers=headers)
    assert response.status_code == 404
    assert response.json["success"] is False
    assert "Item not found" in response.json["error"]


def test_get_qrcode_nonexistent(client, seeded_item, app) -> None:
    """Test non-existent item yields 404."""
    from app.api.auth import generate_internal_jwt

    user_id = seeded_item["owner_id"]

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/qrcode/99999", headers=headers)
    assert response.status_code == 404
    assert response.json["success"] is False
    assert "Item not found" in response.json["error"]
