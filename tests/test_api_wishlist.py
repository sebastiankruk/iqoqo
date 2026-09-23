# tests/test_api_wishlist.py
"""Tests for the dedicated /api/wishlist REST blueprint.

Covers wishlist-api-separation Tasks 2.1–2.3:
  - GET /api/wishlist: list with pagination, filtering (status, work_type, medium_type, search q)
  - POST /api/wishlist: create with work_id, optional expression_id, optional manifestation_id
  - GET /api/wishlist/<id>: retrieve single entry with FRBR enrichment
  - PUT /api/wishlist/<id>: update status, visibility, bound expression/manifestation
  - DELETE /api/wishlist/<id>: remove entry
  - FRBR hierarchy validation (manifestation must belong to expression, expression to work)
  - F15 Complex Works and F16 Container Works hierarchy support
  - Auth: unauthenticated returns 401, other user's entries return 404
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
from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Manifestation, Permission, Role, User, UserWorkIntent, Work, WorkPart, db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wishlist_setup(app):
    """Seed database with a user, works, expressions, and manifestations for wishlist tests."""
    with app.app_context():
        # Ensure user role with write:item permission exists
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
        db.session.flush()

        # Primary test user
        user = User(email="wishlist_test@iqoqo.local", display_name="Wishlist Tester")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Second user (for auth boundary tests)
        user2 = User(email="wishlist_other@iqoqo.local", display_name="Other User")
        user2.roles.append(user_role)
        db.session.add(user2)
        db.session.flush()

        # Work 1: Book with English and French expressions
        work1 = Work(title="The Great Novel", meta={"authors": ["Jane Doe"], "work_type": "TextWork"})
        db.session.add(work1)
        db.session.flush()

        expr_en = Expression(work_id=work1.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(expr_en)
        db.session.flush()

        manif_en = Manifestation(
            expression_id=expr_en.id,
            isbn13="9781234567890",
            meta={"format": MediaFormat.BOOK},
        )
        db.session.add(manif_en)
        db.session.flush()

        expr_fr = Expression(work_id=work1.id, content_type=MediaCategory.TEXT, language="fr")
        db.session.add(expr_fr)
        db.session.flush()

        manif_fr = Manifestation(
            expression_id=expr_fr.id,
            isbn13="9780987654321",
            meta={"format": MediaFormat.BOOK},
        )
        db.session.add(manif_fr)
        db.session.flush()

        # Work 2: Audio work (vinyl)
        work2 = Work(title="Symphony No. 5", meta={"authors": ["Beethoven"], "work_type": "AudioWork"})
        db.session.add(work2)
        db.session.flush()

        expr_audio = Expression(work_id=work2.id, content_type=MediaCategory.MUSIC)
        db.session.add(expr_audio)
        db.session.flush()

        manif_vinyl = Manifestation(
            expression_id=expr_audio.id,
            meta={"format": MediaFormat.VINYL, "medium_type": "Vinyl"},
        )
        db.session.add(manif_vinyl)
        db.session.flush()

        # Work 3: Board game
        work3 = Work(title="Epic Board Game", meta={"authors": ["Game Designer"], "work_type": "GameWork"})
        db.session.add(work3)
        db.session.flush()

        expr_game = Expression(work_id=work3.id, content_type=MediaCategory.BOARD_GAME)
        db.session.add(expr_game)
        db.session.flush()

        manif_game = Manifestation(
            expression_id=expr_game.id,
            meta={"format": MediaFormat.BOARD_GAME},
        )
        db.session.add(manif_game)
        db.session.flush()

        # Pre-existing intent for user1
        existing_intent = UserWorkIntent(
            user_id=user.id,
            work_id=work1.id,
            status="want_to_read",
        )
        db.session.add(existing_intent)

        # Pre-existing intent for user2 (for auth boundary tests)
        other_intent = UserWorkIntent(
            user_id=user2.id,
            work_id=work2.id,
            status="want_to_listen",
        )
        db.session.add(other_intent)

        db.session.commit()
        return {
            "user_id": user.id,
            "user2_id": user2.id,
            "work1_id": work1.id,
            "work2_id": work2.id,
            "work3_id": work3.id,
            "expr_en_id": expr_en.id,
            "expr_fr_id": expr_fr.id,
            "expr_audio_id": expr_audio.id,
            "manif_en_id": manif_en.id,
            "manif_fr_id": manif_fr.id,
            "manif_vinyl_id": manif_vinyl.id,
            "manif_game_id": manif_game.id,
            "existing_intent_id": existing_intent.id,
            "other_intent_id": other_intent.id,
        }


def _headers(app, user_id):
    """Generate JWT auth headers for a given user ID."""
    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Task 2.1 — GET /api/wishlist (list with pagination and filtering)
# ---------------------------------------------------------------------------


class TestGetWishlist:
    """GET /api/wishlist returns the authenticated user's wishlist entries."""

    def test_unauthenticated_returns_401(self, client):
        """Given no auth header, GET /api/wishlist returns 401."""
        response = client.get("/api/wishlist")
        assert response.status_code == 401

    def test_list_wishlist_entries(self, client, wishlist_setup, app):
        """Given an authenticated user with one intent, GET /api/wishlist returns that entry."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist", headers=headers)
        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        entries = data["data"]
        assert isinstance(entries, list)
        assert len(entries) >= 1
        # The pre-existing intent should be present
        work_ids = [e["work_id"] for e in entries]
        assert wishlist_setup["work1_id"] in work_ids

    def test_wishlist_does_not_include_other_users_entries(self, client, wishlist_setup, app):
        """Given user1 requests their wishlist, user2's intents are NOT returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        work_ids = [e["work_id"] for e in entries]
        assert wishlist_setup["work2_id"] not in work_ids

    def test_pagination(self, client, wishlist_setup, app):
        """Given pagination params, GET /api/wishlist returns correct page/limit metadata."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?page=1&limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json
        # Pagination metadata should be present
        assert "meta" in data or "pagination" in data

    def test_filter_by_status(self, client, wishlist_setup, app):
        """Given status filter, only matching intents are returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?status=want_to_read", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        for entry in entries:
            assert entry["status"] == "want_to_read"

    def test_filter_by_work_type(self, client, wishlist_setup, app):
        """Given work_type filter, only matching intents are returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?work_type=AudioWork", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        # user1 has no AudioWork intents, so should be empty
        assert len(entries) == 0

    def test_filter_by_medium_type(self, client, wishlist_setup, app):
        """Given medium_type filter, only matching intents are returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?medium_type=Vinyl", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        # user1 has no Vinyl intents, so should be empty
        assert len(entries) == 0

    def test_search_query(self, client, wishlist_setup, app):
        """Given search query q, only matching intents are returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?q=Great", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        assert len(entries) >= 1
        assert entries[0]["work"]["title"] == "The Great Novel"

    def test_search_query_no_match(self, client, wishlist_setup, app):
        """Given search query with no match, empty list is returned."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist?q=NonexistentBookXYZ", headers=headers)
        assert response.status_code == 200
        entries = response.json["data"]
        assert len(entries) == 0


# ---------------------------------------------------------------------------
# Task 2.1 — POST /api/wishlist (create)
# ---------------------------------------------------------------------------


class TestPostWishlist:
    """POST /api/wishlist creates a new wishlist entry."""

    def test_unauthenticated_returns_401(self, client, wishlist_setup):
        """Given no auth header, POST /api/wishlist returns 401."""
        response = client.post("/api/wishlist", json={"work_id": 999})
        assert response.status_code == 401

    def test_create_work_level_intent(self, client, wishlist_setup, app):
        """Given a valid work_id, POST creates a work-level intent."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={"work_id": wishlist_setup["work3_id"]},
            headers=headers,
        )
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["work_id"] == wishlist_setup["work3_id"]
        assert data["id"] > 0  # Positive ID (no negative IDs)

        # Verify in DB
        with app.app_context():
            intent = UserWorkIntent.query.filter_by(
                user_id=wishlist_setup["user_id"],
                work_id=wishlist_setup["work3_id"],
            ).first()
            assert intent is not None

    def test_create_with_expression(self, client, wishlist_setup, app):
        """Given work_id + expression_id, POST binds to a specific F2 realization."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work1_id"],
                "expression_id": wishlist_setup["expr_fr_id"],
            },
            headers=headers,
        )
        # This may return 200/201 or 409 if the work-level intent already exists
        # (depends on unique constraint handling). The French expression intent
        # is a distinct tuple so it should succeed.
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["expression_id"] == wishlist_setup["expr_fr_id"]

    def test_create_with_expression_and_manifestation(self, client, wishlist_setup, app):
        """Given work_id + expression_id + manifestation_id, POST binds to a specific F3 embodiment."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work1_id"],
                "expression_id": wishlist_setup["expr_en_id"],
                "manifestation_id": wishlist_setup["manif_en_id"],
            },
            headers=headers,
        )
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["manifestation_id"] == wishlist_setup["manif_en_id"]

    def test_create_missing_work_id_returns_400(self, client, wishlist_setup, app):
        """Given no work_id, POST returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={"expression_id": wishlist_setup["expr_en_id"]},
            headers=headers,
        )
        assert response.status_code == 400

    def test_create_invalid_work_id_returns_404(self, client, wishlist_setup, app):
        """Given a non-existent work_id, POST returns 404."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={"work_id": 999999},
            headers=headers,
        )
        assert response.status_code == 404

    def test_create_duplicate_returns_409(self, client, wishlist_setup, app):
        """Given a duplicate (user+work+expression+manifestation), POST returns 409."""
        headers = _headers(app, wishlist_setup["user_id"])
        # The existing intent is work1 with no expression/manifestation
        response = client.post(
            "/api/wishlist",
            json={"work_id": wishlist_setup["work1_id"]},
            headers=headers,
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Task 2.1 — GET /api/wishlist/<id> (retrieve single entry)
# ---------------------------------------------------------------------------


class TestGetWishlistDetail:
    """GET /api/wishlist/<id> retrieves a single wishlist entry with FRBR enrichment."""

    def test_unauthenticated_returns_401(self, client, wishlist_setup):
        """Given no auth header, GET /api/wishlist/<id> returns 401."""
        response = client.get(f"/api/wishlist/{wishlist_setup['existing_intent_id']}")
        assert response.status_code == 401

    def test_get_existing_entry(self, client, wishlist_setup, app):
        """Given a valid intent ID, GET returns the entry with FRBR enrichment."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["id"] == wishlist_setup["existing_intent_id"]
        assert data["work_id"] == wishlist_setup["work1_id"]
        assert data["status"] == "want_to_read"
        # FRBR enrichment: work data should be included
        assert "work" in data
        assert data["work"]["title"] == "The Great Novel"

    def test_get_nonexistent_returns_404(self, client, wishlist_setup, app):
        """Given a non-existent intent ID, GET returns 404."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get("/api/wishlist/999999", headers=headers)
        assert response.status_code == 404

    def test_get_other_users_entry_returns_404(self, client, wishlist_setup, app):
        """Given another user's intent ID, GET returns 404 (BOLA protection)."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.get(
            f"/api/wishlist/{wishlist_setup['other_intent_id']}",
            headers=headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task 2.1 — PUT /api/wishlist/<id> (update)
# ---------------------------------------------------------------------------


class TestPutWishlist:
    """PUT /api/wishlist/<id> updates a wishlist entry."""

    def test_unauthenticated_returns_401(self, client, wishlist_setup):
        """Given no auth header, PUT /api/wishlist/<id> returns 401."""
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"status": "reading"},
        )
        assert response.status_code == 401

    def test_update_status(self, client, wishlist_setup, app):
        """Given a valid status update, PUT changes the intent status."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"status": "reading"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["status"] == "reading"

        with app.app_context():
            intent = db.session.get(UserWorkIntent, wishlist_setup["existing_intent_id"])
            assert intent.status == "reading"

    def test_update_visibility(self, client, wishlist_setup, app):
        """Given is_hidden=true, PUT updates the visibility flag."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"is_hidden": True},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["is_hidden"] is True

        with app.app_context():
            intent = db.session.get(UserWorkIntent, wishlist_setup["existing_intent_id"])
            assert intent.is_hidden is True

    def test_update_bound_expression(self, client, wishlist_setup, app):
        """Given a valid expression_id, PUT binds the intent to a specific F2 realization."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"expression_id": wishlist_setup["expr_fr_id"]},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["expression_id"] == wishlist_setup["expr_fr_id"]

    def test_update_bound_manifestation(self, client, wishlist_setup, app):
        """Given valid expression_id + manifestation_id, PUT binds to a specific F3 embodiment."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={
                "expression_id": wishlist_setup["expr_en_id"],
                "manifestation_id": wishlist_setup["manif_en_id"],
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert data["manifestation_id"] == wishlist_setup["manif_en_id"]

    def test_update_invalid_status_returns_400(self, client, wishlist_setup, app):
        """Given an invalid status, PUT returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"status": "invalid_status_xyz"},
            headers=headers,
        )
        assert response.status_code == 400

    def test_update_other_users_entry_returns_404(self, client, wishlist_setup, app):
        """Given another user's intent ID, PUT returns 404 (BOLA protection)."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            f"/api/wishlist/{wishlist_setup['other_intent_id']}",
            json={"status": "reading"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_update_nonexistent_returns_404(self, client, wishlist_setup, app):
        """Given a non-existent intent ID, PUT returns 404."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.put(
            "/api/wishlist/999999",
            json={"status": "reading"},
            headers=headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task 2.1 — DELETE /api/wishlist/<id>
# ---------------------------------------------------------------------------


class TestDeleteWishlist:
    """DELETE /api/wishlist/<id> removes a wishlist entry."""

    def test_unauthenticated_returns_401(self, client, wishlist_setup):
        """Given no auth header, DELETE /api/wishlist/<id> returns 401."""
        response = client.delete(f"/api/wishlist/{wishlist_setup['existing_intent_id']}")
        assert response.status_code == 401

    def test_delete_existing_entry(self, client, wishlist_setup, app):
        """Given a valid intent ID, DELETE removes the entry."""
        headers = _headers(app, wishlist_setup["user_id"])
        intent_id = wishlist_setup["existing_intent_id"]
        response = client.delete(f"/api/wishlist/{intent_id}", headers=headers)
        assert response.status_code == 200
        assert response.json["success"] is True

        with app.app_context():
            intent = db.session.get(UserWorkIntent, intent_id)
            assert intent is None

    def test_delete_other_users_entry_returns_404(self, client, wishlist_setup, app):
        """Given another user's intent ID, DELETE returns 404 (BOLA protection)."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.delete(
            f"/api/wishlist/{wishlist_setup['other_intent_id']}",
            headers=headers,
        )
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, wishlist_setup, app):
        """Given a non-existent intent ID, DELETE returns 404."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.delete("/api/wishlist/999999", headers=headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Task 2.3 — FRBR hierarchy validation
# ---------------------------------------------------------------------------


class TestFrbrHierarchyValidation:
    """Verify FRBR hierarchy validation: manifestation must belong to expression, expression to work."""

    def test_expression_not_belonging_to_work_rejected(self, client, wishlist_setup, app):
        """Given an expression_id that doesn't belong to the work_id, POST returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        # work3 (board game) with expr_en (from work1 - text)
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work3_id"],
                "expression_id": wishlist_setup["expr_en_id"],
            },
            headers=headers,
        )
        assert response.status_code == 400

    def test_manifestation_not_belonging_to_expression_rejected(self, client, wishlist_setup, app):
        """Given a manifestation_id that doesn't belong to the expression_id, POST returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        # expr_en with manif_vinyl (from expr_audio)
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work1_id"],
                "expression_id": wishlist_setup["expr_en_id"],
                "manifestation_id": wishlist_setup["manif_vinyl_id"],
            },
            headers=headers,
        )
        assert response.status_code == 400

    def test_manifestation_without_expression_rejected(self, client, wishlist_setup, app):
        """Given a manifestation_id without expression_id, POST returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work1_id"],
                "manifestation_id": wishlist_setup["manif_en_id"],
            },
            headers=headers,
        )
        assert response.status_code == 400

    def test_update_hierarchy_violation_rejected(self, client, wishlist_setup, app):
        """Given an update that violates FRBR hierarchy, PUT returns 400."""
        headers = _headers(app, wishlist_setup["user_id"])
        # Try to bind the existing intent to an expression from a different work
        response = client.put(
            f"/api/wishlist/{wishlist_setup['existing_intent_id']}",
            json={"expression_id": wishlist_setup["expr_audio_id"]},
            headers=headers,
        )
        assert response.status_code == 400

    def test_valid_hierarchy_accepted(self, client, wishlist_setup, app):
        """Given a valid FRBR hierarchy (work → expression → manifestation), POST succeeds."""
        headers = _headers(app, wishlist_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": wishlist_setup["work1_id"],
                "expression_id": wishlist_setup["expr_fr_id"],
                "manifestation_id": wishlist_setup["manif_fr_id"],
            },
            headers=headers,
        )
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Task 2.3 — F15 Complex Works and F16 Container Works
# ---------------------------------------------------------------------------


class TestComplexAndContainerWorks:
    """Verify F15 Complex Works and F16 Container Works hierarchy support."""

    @pytest.fixture
    def complex_work_setup(self, app):
        """Seed a container work (F16) with part works (F15)."""
        with app.app_context():
            user_role = Role.query.filter_by(name="user").first()
            user = User.query.filter_by(email="wishlist_test@iqoqo.local").first()
            if not user:
                user = User(email="complex_work_test@iqoqo.local", display_name="Complex Tester")
                if user_role:
                    user.roles.append(user_role)
                db.session.add(user)
                db.session.flush()

            # Container work (F16) - e.g., a box set
            container = Work(
                title="Complete Series Box Set",
                meta={"authors": ["Series Author"], "work_type": "TextWork"},
            )
            db.session.add(container)
            db.session.flush()

            # Part work (F15) - e.g., Volume 1
            part1 = Work(
                title="Series Volume 1",
                meta={"authors": ["Series Author"], "work_type": "TextWork"},
            )
            db.session.add(part1)
            db.session.flush()

            # Link part to container via WorkPart
            work_part = WorkPart(
                container_work_id=container.id,
                part_work_id=part1.id,
                sequence=1,
            )
            db.session.add(work_part)

            expr = Expression(work_id=part1.id, content_type=MediaCategory.TEXT)
            db.session.add(expr)
            db.session.flush()

            manif = Manifestation(expression_id=expr.id, meta={"format": MediaFormat.BOOK})
            db.session.add(manif)
            db.session.flush()

            db.session.commit()
            return {
                "user_id": user.id,
                "container_id": container.id,
                "part1_id": part1.id,
                "expression_id": expr.id,
                "manifestation_id": manif.id,
            }

    def test_intent_for_part_work(self, client, complex_work_setup, app):
        """Given a part work (F15), POST creates an intent for that specific part."""
        headers = _headers(app, complex_work_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={"work_id": complex_work_setup["part1_id"]},
            headers=headers,
        )
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["work_id"] == complex_work_setup["part1_id"]

    def test_intent_for_container_work(self, client, complex_work_setup, app):
        """Given a container work (F16), POST creates an intent for the whole container."""
        headers = _headers(app, complex_work_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={"work_id": complex_work_setup["container_id"]},
            headers=headers,
        )
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["work_id"] == complex_work_setup["container_id"]

    def test_intent_for_specific_manifestation_of_part(self, client, complex_work_setup, app):
        """Given a part work with specific manifestation, POST binds to F3 level."""
        headers = _headers(app, complex_work_setup["user_id"])
        response = client.post(
            "/api/wishlist",
            json={
                "work_id": complex_work_setup["part1_id"],
                "expression_id": complex_work_setup["expression_id"],
                "manifestation_id": complex_work_setup["manifestation_id"],
            },
            headers=headers,
        )
        assert response.status_code in (200, 201)
        data = response.json["data"]
        assert data["manifestation_id"] == complex_work_setup["manifestation_id"]
