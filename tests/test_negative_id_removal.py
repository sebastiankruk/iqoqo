# tests/test_negative_id_removal.py
"""Tests for the removal of negative-ID hack from Items API and access control.

Covers wishlist-api-separation Tasks 3.1–3.4:
  - GET /api/items returns ONLY physical items (no virtual/wishlist)
  - Negative IDs to /api/items/<id> return 404 or 422
  - item_access.py: get_accessible_item rejects negative IDs
  - schemas.py: validation rejects non-positive IDs
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#

import pytest
from pydantic import ValidationError

from app.api.auth import generate_internal_jwt
from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, UserWorkIntent, Work, db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mixed_setup(app):
    """Seed database with both physical items and wishlist intents for the same user."""
    with app.app_context():
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)

        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        if write_perm not in user_role.permissions:
            user_role.permissions.append(write_perm)

        delete_perm = Permission.query.filter_by(name="delete:item").first()
        if not delete_perm:
            delete_perm = Permission(name="delete:item")
            db.session.add(delete_perm)
        if delete_perm not in user_role.permissions:
            user_role.permissions.append(delete_perm)

        db.session.flush()

        user = User(email="neg_id_test@iqoqo.local", display_name="Neg ID Tester")
        user.set_password("test-password")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Physical item
        work1 = Work(title="Physical Book", meta={"authors": ["Author A"]})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type=MediaCategory.TEXT)
        db.session.add(expr1)
        db.session.flush()
        manif1 = Manifestation(expression_id=expr1.id, isbn13="9781111111111", meta={"format": MediaFormat.BOOK})
        db.session.add(manif1)
        db.session.flush()
        item1 = Item(manifestation_id=manif1.id, owner_id=user.id, status="available")
        db.session.add(item1)

        # Wishlist intent (UserWorkIntent)
        work2 = Work(title="Wishlist Book", meta={"authors": ["Author B"]})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type=MediaCategory.TEXT)
        db.session.add(expr2)
        db.session.flush()
        manif2 = Manifestation(expression_id=expr2.id, isbn13="9782222222222", meta={"format": MediaFormat.BOOK})
        db.session.add(manif2)
        db.session.flush()
        intent = UserWorkIntent(user_id=user.id, work_id=work2.id, status="want_to_read")
        db.session.add(intent)

        db.session.commit()
        return {
            "user_id": user.id,
            "item_id": item1.id,
            "intent_id": intent.id,
            "work1_id": work1.id,
            "work2_id": work2.id,
        }


def _headers(app, user_id):
    """Generate JWT auth headers for a given user ID."""
    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Task 3.1 — GET /api/items returns ONLY physical items
# ---------------------------------------------------------------------------


class TestGetItemsPhysicalOnly:
    """GET /api/items must return ONLY physical Item records, no virtual wishlist items.

    These tests verify the expected behavior AFTER the wishlist-api-separation change.
    They are marked xfail until the implementation removes virtual item synthesis from get_items().
    """

    @pytest.mark.xfail(reason="Virtual items still included until Task 3.1 implementation")
    def test_items_list_excludes_virtual(self, client, mixed_setup, app):
        """Given a user with both physical items and intents, GET /api/items returns only physical items."""
        headers = _headers(app, mixed_setup["user_id"])
        response = client.get("/api/items", headers=headers)
        assert response.status_code == 200
        data = response.json["data"]

        # No virtual items should be present
        virtual_items = [i for i in data if i.get("is_virtual")]
        assert len(virtual_items) == 0, "GET /api/items should not include virtual/wishlist items"

        # Physical item should be present
        physical_items = [i for i in data if not i.get("is_virtual")]
        assert len(physical_items) >= 1
        titles = [i.get("title") for i in physical_items]
        assert "Physical Book" in titles

    @pytest.mark.xfail(reason="Virtual items still included until Task 3.1 implementation")
    def test_items_list_with_wish_list_status_filter(self, client, mixed_setup, app):
        """Given statuses=wish_list filter, GET /api/items should NOT return virtual items."""
        headers = _headers(app, mixed_setup["user_id"])
        response = client.get("/api/items?statuses=wish_list", headers=headers)
        assert response.status_code == 200
        data = response.json["data"]

        # After separation, no virtual items should appear even with wish_list filter
        virtual_items = [i for i in data if i.get("is_virtual")]
        assert len(virtual_items) == 0

    @pytest.mark.xfail(reason="Virtual items still included until Task 3.1 implementation")
    def test_items_list_no_negative_ids(self, client, mixed_setup, app):
        """Given a user with intents, no returned item should have a negative ID."""
        headers = _headers(app, mixed_setup["user_id"])
        response = client.get("/api/items", headers=headers)
        assert response.status_code == 200
        data = response.json["data"]

        for item in data:
            assert item["id"] > 0, f"Item ID should be positive, got {item['id']}"


# ---------------------------------------------------------------------------
# Task 3.2 — Negative IDs to /api/items/<id> return 404 or 422
# ---------------------------------------------------------------------------


class TestNegativeIdRejection:
    """Negative IDs to /api/items/<id> endpoints must return 404 or 422.

    These tests verify the expected behavior AFTER the wishlist-api-separation change.
    They are marked xfail until the implementation removes negative-ID handling.
    """

    @pytest.mark.xfail(reason="Negative IDs still handled until Task 3.2 implementation")
    def test_get_item_negative_id_returns_404_or_422(self, client, mixed_setup, app):
        """Given a negative ID, GET /api/items/<negative_id> returns 404 or 422."""
        headers = _headers(app, mixed_setup["user_id"])
        negative_id = -mixed_setup["intent_id"]
        response = client.get(f"/api/items/{negative_id}", headers=headers)
        assert response.status_code in (404, 422), f"Expected 404 or 422 for negative ID, got {response.status_code}"

    @pytest.mark.xfail(reason="Negative IDs still handled until Task 3.2 implementation")
    def test_update_item_negative_id_returns_404_or_422(self, client, mixed_setup, app):
        """Given a negative ID, PUT /api/items/<negative_id> returns 404 or 422."""
        headers = _headers(app, mixed_setup["user_id"])
        negative_id = -mixed_setup["intent_id"]
        response = client.put(
            f"/api/items/{negative_id}",
            json={"status": "reading"},
            headers=headers,
        )
        assert response.status_code in (400, 404, 422), f"Expected 400/404/422 for negative ID update, got {response.status_code}"

    @pytest.mark.xfail(reason="Negative IDs still handled until Task 3.2 implementation")
    def test_delete_item_negative_id_returns_404_or_422(self, client, mixed_setup, app):
        """Given a negative ID, DELETE /api/items/<negative_id> returns 404 or 422."""
        headers = _headers(app, mixed_setup["user_id"])
        negative_id = -mixed_setup["intent_id"]
        response = client.delete(f"/api/items/{negative_id}", headers=headers)
        assert response.status_code in (400, 404, 422), f"Expected 400/404/422 for negative ID delete, got {response.status_code}"

    def test_zero_id_returns_400_or_404(self, client, mixed_setup, app):
        """Given ID=0, endpoints return 400 or 404 (0 is not a valid ID)."""
        headers = _headers(app, mixed_setup["user_id"])
        response = client.get("/api/items/0", headers=headers)
        assert response.status_code in (400, 404, 422)

    def test_qrcode_negative_id_returns_404(self, client, mixed_setup, app):
        """Given a negative ID, GET /api/qrcode/<negative_id> returns 404."""
        headers = _headers(app, mixed_setup["user_id"])
        negative_id = -mixed_setup["intent_id"]
        response = client.get(f"/api/qrcode/{negative_id}", headers=headers)
        # QR code endpoint already rejects negative IDs (no physical copy to tag)
        assert response.status_code in (400, 404, 422)

    def test_item_logs_negative_id_returns_empty_or_404(self, client, mixed_setup, app):
        """Given a negative ID, GET /api/items/<negative_id>/logs returns empty or 404."""
        headers = _headers(app, mixed_setup["user_id"])
        negative_id = -mixed_setup["intent_id"]
        response = client.get(f"/api/items/{negative_id}/logs", headers=headers)
        # After removal, negative IDs should not be processed
        assert response.status_code in (200, 400, 404, 422)
        if response.status_code == 200:
            # If 200, data should be empty (no logs for non-existent physical item)
            data = response.json.get("data", [])
            assert data == [] or data is None


# ---------------------------------------------------------------------------
# Task 3.3 — item_access.py rejects negative IDs
# ---------------------------------------------------------------------------


class TestItemAccessNegativeIdRejection:
    """Verify item_access module rejects negative IDs.

    These tests verify the expected behavior AFTER the wishlist-api-separation change.
    They are marked xfail until the implementation removes negative-ID resolution.
    """

    @pytest.mark.xfail(reason="Negative IDs still resolved until Task 3.3 implementation")
    def test_verify_item_ownership_rejects_negative_id(self, app, mixed_setup):
        """Given a negative item_id, verify_item_ownership returns False."""
        from app.core.item_access import verify_item_ownership

        with app.app_context():
            negative_id = -mixed_setup["intent_id"]
            result = verify_item_ownership(negative_id, mixed_setup["user_id"])
            # After removal, negative IDs should return False (not resolve to UserWorkIntent)
            assert result is False, "verify_item_ownership should reject negative IDs"

    def test_verify_item_ownership_positive_id_works(self, app, mixed_setup):
        """Given a positive item_id owned by the user, verify_item_ownership returns True."""
        from app.core.item_access import verify_item_ownership

        with app.app_context():
            result = verify_item_ownership(mixed_setup["item_id"], mixed_setup["user_id"])
            assert result is True

    def test_verify_item_ownership_nonexistent_returns_false(self, app, mixed_setup):
        """Given a non-existent positive item_id, verify_item_ownership returns False."""
        from app.core.item_access import verify_item_ownership

        with app.app_context():
            result = verify_item_ownership(999999, mixed_setup["user_id"])
            assert result is False


# ---------------------------------------------------------------------------
# Task 3.4 — schemas.py validation rejects non-positive IDs
# ---------------------------------------------------------------------------


class TestSchemaNonPositiveIdRejection:
    """Verify Pydantic schemas reject non-positive IDs."""

    def test_item_lend_schema_rejects_zero_id(self):
        """Given item_id=0, ItemLendSchema raises ValidationError."""
        from app.api.schemas import ItemLendSchema

        with pytest.raises(ValidationError):
            ItemLendSchema(item_id=0)

    def test_item_lend_schema_rejects_negative_id(self):
        """Given item_id=-1, ItemLendSchema raises ValidationError."""
        from app.api.schemas import ItemLendSchema

        with pytest.raises(ValidationError):
            ItemLendSchema(item_id=-1)

    def test_item_lend_schema_accepts_positive_id(self):
        """Given item_id=1, ItemLendSchema validates successfully."""
        from app.api.schemas import ItemLendSchema

        schema = ItemLendSchema(item_id=1)
        assert schema.item_id == 1

    def test_item_create_schema_rejects_zero_id(self):
        """Given id=0 in ItemCreateSchema, validation raises ValidationError."""
        from app.api.schemas import ItemCreateSchema

        with pytest.raises(ValidationError):
            ItemCreateSchema(id=0)

    @pytest.mark.xfail(reason="ItemCreateSchema does not yet reject negative IDs until Task 3.4")
    def test_item_create_schema_rejects_negative_id(self):
        """Given id=-5 in ItemCreateSchema, validation raises ValidationError."""
        from app.api.schemas import ItemCreateSchema

        with pytest.raises(ValidationError):
            ItemCreateSchema(id=-5)
