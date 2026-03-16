"""Tests for Phase 2: React frontend integration points.

Verifies that all API endpoints consumed by the Next.js frontend return the
expected JSON shape, status codes, and field names.  These are integration
tests that run against an in-memory SQLite database so no live PostgreSQL or
Docker instance is required.
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

from app.api.auth import generate_internal_jwt
from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, User, Work, db

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally
# pylint: disable=unused-argument      # fixtures used for side-effects/setup


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_library(app):
    """Seed an in-memory library with items spanning several statuses."""
    with app.app_context():
        test_user = User(email="frontend_test@iqoqo.local", display_name="Frontend Tester")
        db.session.add(test_user)
        db.session.commit()  # Commit to generate the UUID

        work1 = Work(title="Dune", meta={"authors": ["Frank Herbert"], "categories": ["Sci-Fi"]})
        work2 = Work(title="Recursion", meta={"authors": ["Blake Crouch"], "categories": ["Thriller"]})
        db.session.add_all([work1, work2])
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="text", language="en", meta={})
        expr2 = Expression(work_id=work2.id, content_type="text", language="en", meta={})
        db.session.add_all([expr1, expr2])
        db.session.flush()

        mani1 = Manifestation(
            expression_id=expr1.id,
            isbn13="9780441013593",
            meta={"Title": "Dune", "Authors": ["Frank Herbert"]},
        )
        mani2 = Manifestation(
            expression_id=expr2.id,
            isbn13="9781524759865",
            meta={"Title": "Recursion", "Authors": ["Blake Crouch"]},
        )
        mani3 = Manifestation(
            expression_id=expr1.id,
            isbn13="9780441013594",
            meta={"Title": "Dune Messiah", "Authors": ["Frank Herbert"]},
        )
        db.session.add_all([mani1, mani2, mani3])
        db.session.flush()

        # available, lent, wish_list items to test stat counts
        item_available = Item(manifestation_id=mani1.id, owner_id=test_user.id, status="available", meta={})
        item_lent = Item(manifestation_id=mani2.id, owner_id=test_user.id, status="lent", meta={})
        item_wish = Item(manifestation_id=mani3.id, owner_id=test_user.id, status="wish_list", meta={})
        db.session.add_all([item_available, item_lent, item_wish])
        db.session.commit()

        yield {
            "user": test_user,
            "work1": work1,
            "work2": work2,
            "mani1": mani1,
            "mani2": mani2,
            "mani3": mani3,
            "item_available": item_available,
            "item_lent": item_lent,
            "item_wish": item_wish,
        }


@pytest.fixture
def auth_headers(populated_library):
    """Generate authentication headers for the user in the populated library."""
    token = generate_internal_jwt(populated_library["user"])
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# DataManager.get_stats() unit tests
# ===========================================================================


class TestGetStats:
    """Unit tests for DataManager.get_stats() used by GET /api/stats."""

    def test_returns_all_required_ui_fields(self, app, populated_library):
        """get_stats() must include the UI-friendly aliases the dashboard expects."""
        with app.app_context():
            stats = DataManager.get_stats()
            assert "total_items" in stats
            assert "lent_items" in stats
            assert "to_read" in stats

    def test_returns_frbr_entity_counts(self, app, populated_library):
        """get_stats() must also expose raw FRBR entity counts."""
        with app.app_context():
            stats = DataManager.get_stats()
            assert "works" in stats
            assert "expressions" in stats
            assert "manifestations" in stats
            assert "items" in stats

    def test_total_items_equals_item_count(self, app, populated_library):
        """total_items must equal the number of Item rows."""
        with app.app_context():
            stats = DataManager.get_stats()
            assert stats["total_items"] == Item.query.count()
            assert stats["items"] == stats["total_items"]

    def test_lent_items_counts_lent_status(self, app, populated_library):
        """lent_items must count only items with status='lent'."""
        with app.app_context():
            stats = DataManager.get_stats()
            assert stats["lent_items"] == 1

    def test_to_read_counts_wish_list_status(self, app, populated_library):
        """to_read must count only items with status='wish_list'."""
        with app.app_context():
            stats = DataManager.get_stats()
            assert stats["to_read"] == 1

    def test_empty_library_returns_zeros(self, app):
        """All counts are zero when the database is empty."""
        with app.app_context():
            stats = DataManager.get_stats()
            for key in ("total_items", "lent_items", "to_read", "works", "items"):
                assert stats[key] == 0, f"Expected 0 for {key}, got {stats[key]}"


# ===========================================================================
# GET /api/stats endpoint tests
# ===========================================================================


class TestStatsEndpoint:
    """Integration tests for the GET /api/stats endpoint."""

    def test_returns_200(self, client):
        """Endpoint must respond with HTTP 200."""
        response = client.get("/api/stats")
        assert response.status_code == 200

    def test_returns_success_envelope(self, client):
        """Response must use the standard {success, data, error} envelope."""
        response = client.get("/api/stats")
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["error"] is None
        assert isinstance(payload["data"], dict)

    def test_data_contains_ui_fields(self, client):
        """data block must contain the UI-friendly aliases."""
        response = client.get("/api/stats")
        data = response.get_json()["data"]
        assert "total_items" in data
        assert "lent_items" in data
        assert "to_read" in data

    def test_data_contains_frbr_counts(self, client):
        """data block must contain FRBR entity counts."""
        response = client.get("/api/stats")
        data = response.get_json()["data"]
        for field in ("works", "expressions", "manifestations", "items"):
            assert field in data, f"Missing field: {field}"

    def test_stat_values_are_integers(self, client, populated_library):
        """All stat values must be non-negative integers."""
        response = client.get("/api/stats")
        data = response.get_json()["data"]
        for key, value in data.items():
            assert isinstance(value, int), f"{key} is not an int: {value!r}"
            assert value >= 0, f"{key} is negative: {value}"

    def test_stat_counts_reflect_seeded_data(self, client, populated_library):
        """Stats must reflect the three seeded items with different statuses."""
        response = client.get("/api/stats")
        data = response.get_json()["data"]
        assert data["total_items"] == 3
        assert data["lent_items"] == 1
        assert data["to_read"] == 1


# ===========================================================================
# GET /api/items endpoint – shape expected by the collection grid
# ===========================================================================


class TestItemsListEndpoint:
    """Tests for the paginated item list endpoint used by the collection page."""

    def test_returns_200(self, client, auth_headers):
        """Endpoint must respond with HTTP 200."""
        response = client.get("/api/items", headers=auth_headers)
        assert response.status_code == 200

    def test_envelope_structure(self, client, populated_library, auth_headers):
        """Response must include success, data, error, and meta."""
        response = client.get("/api/items", headers=auth_headers)
        payload = response.get_json()
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["meta"] is not None

    def test_pagination_meta_fields(self, client, populated_library, auth_headers):
        """meta block must include page, limit, total, pages."""
        response = client.get("/api/items?page=1&limit=2", headers=auth_headers)
        meta = response.get_json()["meta"]
        for field in ("page", "limit", "total", "pages"):
            assert field in meta, f"Missing meta field: {field}"

    def test_item_has_required_frontend_fields(self, client, populated_library, auth_headers):
        """Each item must expose the fields used by ItemCard in the frontend."""
        response = client.get("/api/items?limit=10", headers=auth_headers)
        items = response.get_json()["data"]
        assert len(items) > 0
        for item in items:
            assert "id" in item
            assert "title" in item
            assert "status" in item
            assert "isbn" in item

    def test_item_status_values_are_valid(self, client, populated_library, auth_headers):
        """item.status must be one of the known backend values."""
        valid_statuses = {"available", "lent", "lost", "wish_list"}
        response = client.get("/api/items?limit=100", headers=auth_headers)
        items = response.get_json()["data"]
        for item in items:
            assert item["status"] in valid_statuses, f"Unexpected status '{item['status']}' for item {item['id']}"

    def test_respects_limit_parameter(self, client, populated_library, auth_headers):
        """?limit= must cap the number of returned items."""
        response = client.get("/api/items?limit=1", headers=auth_headers)
        items = response.get_json()["data"]
        assert len(items) == 1

    def test_item_has_cover_status(self, client, populated_library, auth_headers):
        """Items in the list must include cover_status for the UI overlay."""
        response = client.get("/api/items?limit=1", headers=auth_headers)
        items = response.get_json()["data"]
        assert len(items) > 0
        assert "cover_status" in items[0]


# ===========================================================================
# GET /api/items/<id> endpoint – shape expected by the item detail page
# ===========================================================================


class TestItemDetailEndpoint:
    """Tests for the single-item endpoint used by the item detail page."""

    def test_returns_404_for_unknown_id(self, client):
        """Requesting a non-existent item must return 404."""
        response = client.get("/api/items/999999")
        assert response.status_code == 404

    def test_returns_full_frbr_object(self, client, populated_library):
        """A found item must include the nested work and expression blocks."""
        item_id = populated_library["item_available"].id
        response = client.get(f"/api/items/{item_id}")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert "work" in data
        assert "expression" in data
        assert "manifestation_meta" in data

    def test_work_block_has_title_and_authors(self, client, populated_library):
        """The nested work block must expose title and authors."""
        item_id = populated_library["item_available"].id
        response = client.get(f"/api/items/{item_id}")
        work = response.get_json()["data"]["work"]
        assert "title" in work
        assert "authors" in work

    def test_item_status_preserved(self, client, populated_library):
        """The lent item must surface with status='lent'."""
        item_id = populated_library["item_lent"].id
        response = client.get(f"/api/items/{item_id}")
        data = response.get_json()["data"]
        assert data["status"] == "lent"

    def test_detail_has_cover_status(self, client, populated_library):
        """Item details must include cover_status for the polling hook."""
        item_id = populated_library["item_available"].id
        response = client.get(f"/api/items/{item_id}")
        data = response.get_json()["data"]
        assert "cover_status" in data


# ===========================================================================
# GET /api/health endpoint
# ===========================================================================


class TestHealthEndpoint:
    """Smoke tests for the /api/health endpoint used by monitoring."""

    def test_returns_200(self, client):
        """Health endpoint must always return 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_returns_ok_status(self, client):
        """Response must report status=ok."""
        payload = client.get("/api/health").get_json()
        assert payload.get("status") == "ok"
