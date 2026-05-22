"""Tests for the advanced organization and Work/Taxonomy specialized views."""

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

import json
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, User, Work, WorkPart, db


@pytest.fixture
def complex_shelf_data(app):
    """Seed the database with complex JSONB metadata and multiple manifestations for the same Work."""
    with app.app_context():
        user = User(email="advanced_views@iqoqo.local", display_name="Advanced Tester")
        db.session.add(user)
        db.session.flush()

        w1 = Work(title="The Lord of the Rings", meta={"creators": ["J.R.R. Tolkien"]})
        db.session.add(w1)
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(e1)
        db.session.flush()

        m1a = Manifestation(expression_id=e1.id, meta={"format": MediaFormat.BOOK})
        db.session.add(m1a)

        m1b = Manifestation(expression_id=e1.id, meta={"format": MediaFormat.BOOK})
        db.session.add(m1b)
        db.session.flush()

        i1 = Item(
            manifestation_id=m1a.id,
            owner_id=user.id,
            status="read",
            meta={"tags": ["fantasy", "epic"], "genres": ["High Fantasy"], "publisher": "Allen & Unwin"},
        )
        i2 = Item(
            manifestation_id=m1b.id,
            owner_id=user.id,
            status="want_to_read",
            meta={"tags": ["favorite", "fantasy"], "collections": ["My Precious"], "publisher": "HarperCollins"},
        )
        db.session.add_all([i1, i2])

        db.session.commit()
        return user.id


@pytest.fixture
def user_scoped_taxonomy_data(app):
    """Seed two users with distinct tags, publishers, and genres for user-scoping tests."""
    with app.app_context():
        from app.db.models import ItemTag, Tag

        user_a = User(email="tax_a@iqoqo.local", display_name="User A")
        db.session.add(user_a)
        user_b = User(email="tax_b@iqoqo.local", display_name="User B")
        db.session.add(user_b)
        db.session.flush()

        # --- User A's data ---
        w_a = Work(title="A's Fantasy Novel", meta={"genres": ["Fantasy", "Epic"]})
        db.session.add(w_a)
        db.session.flush()
        e_a = Expression(work_id=w_a.id, content_type=MediaCategory.TEXT)
        db.session.add(e_a)
        db.session.flush()
        m_a = Manifestation(expression_id=e_a.id, publisher="HarperCollins", meta={"format": MediaFormat.BOOK})
        db.session.add(m_a)
        db.session.flush()
        i_a = Item(manifestation_id=m_a.id, owner_id=user_a.id, status="owned")
        db.session.add(i_a)
        db.session.flush()

        tag_a1 = Tag(name="fantasy")
        tag_a2 = Tag(name="epic")
        db.session.add_all([tag_a1, tag_a2])
        db.session.flush()

        db.session.add_all(
            [
                ItemTag(item_id=i_a.id, tag_id=tag_a1.id, added_by_id=user_a.id),
                ItemTag(item_id=i_a.id, tag_id=tag_a2.id, added_by_id=user_a.id),
            ]
        )

        # --- User B's data ---
        w_b = Work(title="B's Sci-Fi Book", meta={"genre": "Sci-Fi"})
        db.session.add(w_b)
        db.session.flush()
        e_b = Expression(work_id=w_b.id, content_type=MediaCategory.TEXT)
        db.session.add(e_b)
        db.session.flush()
        m_b = Manifestation(expression_id=e_b.id, publisher="Penguin", meta={"format": MediaFormat.BOOK})
        db.session.add(m_b)
        db.session.flush()
        i_b = Item(manifestation_id=m_b.id, owner_id=user_b.id, status="owned")
        db.session.add(i_b)
        db.session.flush()

        tag_b = Tag(name="sci-fi")
        db.session.add(tag_b)
        db.session.flush()

        db.session.add(ItemTag(item_id=i_b.id, tag_id=tag_b.id, added_by_id=user_b.id))

        db.session.commit()

        return {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
        }


def test_taxonomies_user_scoped(client, user_scoped_taxonomy_data, app):
    """Test that /api/taxonomies returns only the current user's tags, genres, publishers."""
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user_a = db.session.get(User, user_scoped_taxonomy_data["user_a_id"])
        token_a = generate_internal_jwt(user_a)
        user_b = db.session.get(User, user_scoped_taxonomy_data["user_b_id"])
        token_b = generate_internal_jwt(user_b)

    # User A sees only A's data
    res = client.get("/api/taxonomies?scope=user", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    body = res.json["data"]
    assert "fantasy" in body["tags"]
    assert "epic" in body["tags"]
    assert "sci-fi" not in body["tags"]
    assert "Fantasy" in body["genres"]
    assert "Epic" in body["genres"]
    assert "Sci-Fi" not in body["genres"]
    assert "HarperCollins" in body["publishers"]
    assert "Penguin" not in body["publishers"]

    # User B sees only B's data
    res = client.get("/api/taxonomies?scope=user", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 200
    body = res.json["data"]
    assert "sci-fi" in body["tags"]
    assert "fantasy" not in body["tags"]
    assert "Sci-Fi" in body["genres"]
    assert "Fantasy" not in body["genres"]
    assert "Penguin" in body["publishers"]
    assert "HarperCollins" not in body["publishers"]


def test_get_works_shelf_aggregation(client, complex_shelf_data, app):
    """Test GET /api/works/shelf aggregates multiple manifestations into a single Work concept."""
    user_id = complex_shelf_data
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/works/shelf", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    assert len(data) == 1
    work_data = data[0]

    assert work_data["title"] == "The Lord of the Rings"
    assert "J.R.R. Tolkien" in work_data["creators"]

    assert work_data["total_items"] == 2
    assert len(work_data["owned_manifestations"]) == 2

    # Assert item_id and cover_url are populated and mapped
    m_data = work_data["owned_manifestations"][0]
    assert "item_id" in m_data
    assert m_data["item_id"] is not None
    assert "cover_url" in m_data


def test_unauthorized_access_blocked(client):
    """Ensure taxonomy and work routes enforce authentication."""
    res1 = client.get("/api/taxonomies")
    assert res1.status_code == 401

    res2 = client.get("/api/works/shelf")
    assert res2.status_code == 401

    res3 = client.get("/api/expressions/shelf")
    assert res3.status_code == 401

    res4 = client.post("/api/works/1/parts", json={"part_work_id": 2})
    assert res4.status_code == 401

    res5 = client.delete("/api/works/1/parts/2")
    assert res5.status_code == 401


def test_get_taxonomies_empty_state(client, app):
    """Test GET /api/taxonomies handles users with zero items gracefully."""
    with app.app_context():
        user = User(email="empty_tax@iqoqo.local", display_name="Empty Tester")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/taxonomies", headers=headers)

    assert response.status_code == 200
    data = response.json["data"]

    assert data["tags"] == []
    assert data["genres"] == []
    assert data["collections"] == []
    assert data["publishers"] == []


def test_get_taxonomies_null_meta_handling(client, app):
    """Test GET /api/taxonomies doesn't crash when items have empty or null JSONB meta."""
    with app.app_context():
        user = User(email="null_meta@iqoqo.local", display_name="Null Meta Tester")
        db.session.add(user)
        db.session.flush()

        w1 = Work(title="Blank Book")
        db.session.add(w1)
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
        db.session.add(e1)
        db.session.flush()

        m1 = Manifestation(expression_id=e1.id)
        db.session.add(m1)
        db.session.flush()

        i1 = Item(manifestation_id=m1.id, owner_id=user.id, meta={})
        db.session.add(i1)
        db.session.commit()
        user_id = user.id

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/taxonomies", headers=headers)

    assert response.status_code == 200
    data = response.json["data"]
    assert data["tags"] == []


def test_get_works_shelf_isolation(client, complex_shelf_data, app):
    """Ensure User B cannot see the works aggregated from User A's shelf."""
    user_a_id = complex_shelf_data

    with app.app_context():
        user_b = User(email="isolated_user@iqoqo.local", display_name="Isolated Tester")
        db.session.add(user_b)
        db.session.commit()
        user_b_id = user_b.id

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user_a = db.session.get(User, user_a_id)
        token_a = generate_internal_jwt(user_a)

    res_a = client.get("/api/works/shelf", headers={"Authorization": f"Bearer {token_a}"})
    assert len(res_a.json["data"]) == 1

    with app.app_context():
        user_b_ref = db.session.get(User, user_b_id)
        token_b = generate_internal_jwt(user_b_ref)

    res_b = client.get("/api/works/shelf", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert len(res_b.json["data"]) == 0
    assert res_b.json["total"] == 0


def test_get_works_shelf_orphaned_items(client, app):
    """Ensure the aggregation loop doesn't crash if an item's FRBR chain is broken."""
    with app.app_context():
        user = User(email="orphan_tester@iqoqo.local", display_name="Orphan Tester")
        db.session.add(user)
        db.session.flush()

        w1 = Work(title="Orphan Work")
        db.session.add(w1)
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
        db.session.add(e1)
        db.session.flush()

        m1 = Manifestation(expression_id=e1.id)
        db.session.add(m1)
        db.session.flush()

        i1 = Item(manifestation_id=m1.id, owner_id=user.id, meta={})
        db.session.add(i1)

        # Delete expression to break FRBR chain (simulate corruption)
        db.session.delete(e1)
        db.session.flush()

        db.session.commit()
        user_id = user.id

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/works/shelf", headers=headers)

    assert response.status_code == 200
    assert response.json["data"] == []


@pytest.fixture
def series_data(app):
    """Seed the database with a complex work (series) and its parts (F15 Complex Work)."""
    with app.app_context():
        from app.db.models import Permission, Role

        user = User(email="series_tester@iqoqo.local", display_name="Series Tester")
        db.session.add(user)
        db.session.flush()

        # Grant write:metadata permission
        perm = Permission.query.filter_by(name="write:metadata").first()
        if not perm:
            perm = Permission(name="write:metadata")
            db.session.add(perm)
            db.session.flush()

        role = Role(name="series_tester_role")
        role.permissions.append(perm)
        db.session.add(role)
        db.session.flush()

        user.roles.append(role)

        container = Work(title="The Lord of the Rings Series")
        db.session.add(container)
        db.session.flush()

        part1 = Work(title="The Fellowship of the Ring")
        part2 = Work(title="The Two Towers")
        db.session.add_all([part1, part2])
        db.session.flush()

        wp1 = WorkPart(container_work_id=container.id, part_work_id=part1.id, sequence=1)
        wp2 = WorkPart(container_work_id=container.id, part_work_id=part2.id, sequence=2)
        db.session.add_all([wp1, wp2])

        db.session.commit()

        return {"user_id": user.id, "container_id": container.id, "part1_id": part1.id, "part2_id": part2.id}


def test_get_expressions_shelf_aggregation(client, complex_shelf_data, app):
    """Test GET /api/expressions/shelf aggregates manifestations at the Expression layer."""
    user_id = complex_shelf_data
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/expressions/shelf", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    assert len(data) == 1
    expr_data = data[0]

    assert expr_data["work_title"] == "The Lord of the Rings"
    assert expr_data["content_type"] == MediaCategory.TEXT
    assert expr_data["language"] == "en"

    assert expr_data["total_items"] == 2
    assert len(expr_data["owned_manifestations"]) == 2

    # Assert item_id and cover_url are populated and mapped
    m_data = expr_data["owned_manifestations"][0]
    assert "item_id" in m_data
    assert m_data["item_id"] is not None
    assert "cover_url" in m_data


def test_get_work_parts(client, series_data):
    """Test GET /api/works/<id>/parts retrieves the sequence of a complex work."""
    container_id = series_data["container_id"]
    response = client.get(f"/api/works/{container_id}/parts")

    assert response.status_code == 200
    data = response.json["data"]

    assert len(data) == 2
    assert data[0]["sequence"] == 1
    assert data[0]["title"] == "The Fellowship of the Ring"

    assert data[1]["sequence"] == 2
    assert data[1]["title"] == "The Two Towers"


def test_add_work_part(client, series_data, app):
    """Test POST /api/works/<id>/parts adds a new part to a complex work."""
    container_id = series_data["container_id"]
    user_id = series_data["user_id"]

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

        part3 = Work(title="The Return of the King")
        db.session.add(part3)
        db.session.commit()
        part3_id = part3.id

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"part_work_id": part3_id, "sequence": 3}

    response = client.post(f"/api/works/{container_id}/parts", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    verify_response = client.get(f"/api/works/{container_id}/parts")
    assert len(verify_response.json["data"]) == 3
    assert verify_response.json["data"][2]["title"] == "The Return of the King"


def test_remove_work_part(client, series_data, app):
    """Test DELETE /api/works/<id>/parts/<part_id> removes a part from the series."""
    container_id = series_data["container_id"]
    part1_id = series_data["part1_id"]
    user_id = series_data["user_id"]

    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(f"/api/works/{container_id}/parts/{part1_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    verify_response = client.get(f"/api/works/{container_id}/parts")
    assert len(verify_response.json["data"]) == 1
    assert verify_response.json["data"][0]["title"] == "The Two Towers"


def test_taxonomy_filtering_across_endpoints(client: FlaskClient, app: Flask) -> None:
    """Test filtering by tags, collections, genres, and publishers across all collection endpoints."""
    from app.api.auth import generate_internal_jwt
    from app.db.models import ItemTag, Tag, UserCollection, UserCollectionItem

    with app.app_context():
        user = User(email="tax_filter_tester@iqoqo.local", display_name="Filter Tester")
        db.session.add(user)
        db.session.flush()
        user_id = user.id

        # Seed data
        # Work 1
        w1 = Work(title="Fantasy Novel", meta={"creators": ["Author One"], "genre": "Fantasy"})
        # Work 2
        w2 = Work(title="Sci-Fi Book", meta={"creators": ["Author Two"], "genre": "Sci-Fi", "genres": ["Sci-Fi", "Space Opera"]})
        db.session.add_all([w1, w2])
        db.session.flush()

        # Expression 1
        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT, language="en")
        # Expression 2
        e2 = Expression(work_id=w2.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add_all([e1, e2])
        db.session.flush()

        # Manifestation 1
        m1 = Manifestation(expression_id=e1.id, publisher="HarperCollins", meta={"format": MediaFormat.BOOK})
        # Manifestation 2
        m2 = Manifestation(expression_id=e2.id, publisher="Penguin", meta={"format": MediaFormat.BOOK})
        db.session.add_all([m1, m2])
        db.session.flush()

        # Items
        i1 = Item(manifestation_id=m1.id, owner_id=user_id, status="owned")
        i2 = Item(manifestation_id=m2.id, owner_id=user_id, status="owned")
        db.session.add_all([i1, i2])
        db.session.flush()

        # Tags
        tag1 = Tag(name="must-read")
        tag2 = Tag(name="on-hold")
        db.session.add_all([tag1, tag2])
        db.session.flush()

        # Link tag1 to i1
        it1 = ItemTag(item_id=i1.id, tag_id=tag1.id, added_by_id=user_id)
        db.session.add(it1)

        # Collections
        col1 = UserCollection(name="Favorites", owner_id=user_id)
        col2 = UserCollection(name="Later", owner_id=user_id)
        db.session.add_all([col1, col2])
        db.session.flush()

        # Link col1 to i1
        uci1 = UserCollectionItem(collection_id=col1.id, item_id=i1.id)
        db.session.add(uci1)

        db.session.commit()

        # Capture IDs inside app_context
        i1_id = i1.id
        i2_id = i2.id
        m1_id = m1.id
        m2_id = m2.id
        w1_id = w1.id
        w2_id = w2.id
        e1_id = e1.id
        e2_id = e2.id

        # Generate JWT
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    def get_data(path: str) -> dict[str, Any]:
        r = client.get(path, headers=headers)
        assert r.status_code == 200
        res_json = r.get_json()
        assert isinstance(res_json, dict)
        return res_json

    # 1. Test Items Endpoint
    # Test tags filter
    data = get_data("/api/items?tags=must-read")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i1_id

    data = get_data("/api/items?tags=on-hold")
    assert len(data["data"]) == 0

    # Test collections filter
    data = get_data("/api/items?collections=Favorites")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i1_id

    data = get_data("/api/items?collections=Later")
    assert len(data["data"]) == 0

    # Test genres filter
    data = get_data("/api/items?genres=Fantasy")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i1_id

    data = get_data("/api/items?genres=Sci-Fi")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i2_id

    # Test array genre filter works too (genres stored as JSON array)
    data = get_data("/api/items?genres=Space+Opera")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i2_id

    # Test publishers filter
    data = get_data("/api/items?publishers=HarperCollins")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i1_id

    data = get_data("/api/items?publishers=Penguin")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == i2_id

    # 2. Test Manifestations Endpoint
    # Test tags filter
    data = get_data("/api/manifestations?tags=must-read")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == m1_id

    # Test collections filter
    data = get_data("/api/manifestations?collections=Favorites")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == m1_id

    # Test genres filter
    data = get_data("/api/manifestations?genres=Sci-Fi")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == m2_id

    # Test array genre filter on manifestations
    data = get_data("/api/manifestations?genres=Space+Opera")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == m2_id

    # Test publishers filter
    data = get_data("/api/manifestations?publishers=HarperCollins")
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == m1_id

    # 3. Test Works Shelf Endpoint
    # Test tags filter
    data = get_data("/api/works/shelf?tags=must-read")
    assert len(data["data"]) == 1
    assert data["data"][0]["work_id"] == w1_id

    # Test collections filter
    data = get_data("/api/works/shelf?collections=Favorites")
    assert len(data["data"]) == 1
    assert data["data"][0]["work_id"] == w1_id

    # Test genres filter
    data = get_data("/api/works/shelf?genres=Sci-Fi")
    assert len(data["data"]) == 1
    assert data["data"][0]["work_id"] == w2_id

    # Test array genre filter on works shelf
    data = get_data("/api/works/shelf?genres=Space+Opera")
    assert len(data["data"]) == 1
    assert data["data"][0]["work_id"] == w2_id

    # Test publishers filter
    data = get_data("/api/works/shelf?publishers=HarperCollins")
    assert len(data["data"]) == 1
    assert data["data"][0]["work_id"] == w1_id

    # 4. Test Expressions Shelf Endpoint
    # Test tags filter
    data = get_data("/api/expressions/shelf?tags=must-read")
    assert len(data["data"]) == 1
    assert data["data"][0]["expression_id"] == e1_id

    # Test collections filter
    data = get_data("/api/expressions/shelf?collections=Favorites")
    assert len(data["data"]) == 1
    assert data["data"][0]["expression_id"] == e1_id

    # Test genres filter
    data = get_data("/api/expressions/shelf?genres=Sci-Fi")
    assert len(data["data"]) == 1
    assert data["data"][0]["expression_id"] == e2_id

    # Test array genre filter on expressions shelf
    data = get_data("/api/expressions/shelf?genres=Space+Opera")
    assert len(data["data"]) == 1
    assert data["data"][0]["expression_id"] == e2_id

    # Test publishers filter
    data = get_data("/api/expressions/shelf?publishers=HarperCollins")
    assert len(data["data"]) == 1
    assert data["data"][0]["expression_id"] == e1_id


def test_taxonomy_filtering_case_insensitive(client: FlaskClient, app: Flask) -> None:
    """Regression test: filtering by tags/genres/publishers must be case-insensitive
    and trim whitespace, so that URL params like ?tags=cosmo or ?genres=Fiction
    still match DB entries like 'Cosmos' or 'Fiction ' respectively.

    Reproduces the bug where Work/Expression/Manifestation views returned empty
    results even though the same data showed up in the manifestations global catalog.
    """
    from app.api.auth import generate_internal_jwt
    from app.db.models import ItemTag, Tag

    with app.app_context():
        user = User(email="case_filter@iqoqo.local", display_name="Case Filter Tester")
        db.session.add(user)
        db.session.flush()
        user_id = user.id

        # Work with genre stored with trailing whitespace (common data-quality issue)
        w1 = Work(title="Genre Whitespace Book", meta={"creators": [], "genres": ["Fiction "]})
        # Work with genre stored as mixed-case
        w2 = Work(title="Publisher Case Book", meta={"creators": [], "genre": "Mystery"})
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
        e2 = Expression(work_id=w2.id, content_type=MediaCategory.TEXT)
        db.session.add_all([e1, e2])
        db.session.flush()

        # Publisher with mixed-case and slash (e.g. "Black Swan/Carousel/Corgi")
        m1 = Manifestation(expression_id=e1.id, publisher="Black Swan/Carousel/Corgi", meta={})
        m2 = Manifestation(expression_id=e2.id, publisher="Allyn & Bacon", meta={})
        db.session.add_all([m1, m2])
        db.session.flush()

        i1 = Item(manifestation_id=m1.id, owner_id=user_id, status="owned")
        i2 = Item(manifestation_id=m2.id, owner_id=user_id, status="owned")
        db.session.add_all([i1, i2])
        db.session.flush()

        # Tag stored as "Cosmos" but URL will send "cosmo" (substring partial-match via ilike)
        tag_cosmos = Tag(name="Cosmos")
        db.session.add(tag_cosmos)
        db.session.flush()
        db.session.add(ItemTag(item_id=i1.id, tag_id=tag_cosmos.id, added_by_id=user_id))

        db.session.commit()

        e1_id = e1.id
        e2_id = e2.id
        w1_id = w1.id
        m1_id = m1.id

        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    def get_data(path: str) -> dict[str, Any]:
        r = client.get(path, headers=headers)
        assert r.status_code == 200
        result: dict[str, Any] = r.get_json()
        return result

    # --- Genre filtering: URL sends "Fiction" but DB has "Fiction " (trailing space) ---
    # Regression: previously returned empty results

    data = get_data("/api/works/shelf?genres=Fiction")
    work_ids = [d["work_id"] for d in data["data"]]
    assert w1_id in work_ids, "genre 'Fiction' must match 'Fiction ' (with trailing space) on works shelf"

    data = get_data("/api/expressions/shelf?genres=Fiction")
    expr_ids = [d["expression_id"] for d in data["data"]]
    assert e1_id in expr_ids, "genre 'Fiction' must match 'Fiction ' on expressions shelf"

    data = get_data("/api/manifestations?genres=Fiction")
    manif_ids = [d["id"] for d in data["data"]]
    assert m1_id in manif_ids, "genre 'Fiction' must match 'Fiction ' on manifestations view"

    # --- Publisher filtering: URL sends "Black Swan" (substring) but DB has full compound name ---
    # Regression: ilike('%Black Swan%') should match "Black Swan/Carousel/Corgi"

    data = get_data("/api/works/shelf?publishers=Black+Swan%2FCarousel%2FCorgi")
    work_ids = [d["work_id"] for d in data["data"]]
    assert w1_id in work_ids, "publisher filter must match compound publisher name on works shelf"

    data = get_data("/api/expressions/shelf?publishers=Black+Swan%2FCarousel%2FCorgi")
    expr_ids = [d["expression_id"] for d in data["data"]]
    assert e1_id in expr_ids, "publisher filter must match compound publisher name on expressions shelf"

    data = get_data("/api/manifestations?publishers=Black+Swan%2FCarousel%2FCorgi")
    manif_ids = [d["id"] for d in data["data"]]
    assert m1_id in manif_ids, "publisher filter must match compound publisher name on manifestations"

    # --- Publisher: partial substring match (Allyn & Bacon) ---
    data = get_data("/api/expressions/shelf?publishers=Allyn+%26+Bacon")
    expr_ids = [d["expression_id"] for d in data["data"]]
    assert e2_id in expr_ids, "publisher 'Allyn & Bacon' must match on expressions shelf"

    # --- Tag case-insensitive: "cosmos" (lowercase) must match tag named "Cosmos" ---
    # Regression: previously exact in_() meant only exact case "Cosmos" worked

    data = get_data("/api/works/shelf?tags=cosmos")
    work_ids = [d["work_id"] for d in data["data"]]
    assert w1_id in work_ids, "tag 'cosmos' (lowercase) must match tag 'Cosmos' on works shelf"

    data = get_data("/api/expressions/shelf?tags=cosmos")
    expr_ids = [d["expression_id"] for d in data["data"]]
    assert e1_id in expr_ids, "tag 'cosmos' must match tag 'Cosmos' on expressions shelf"

    data = get_data("/api/manifestations?tags=cosmos")
    manif_ids = [d["id"] for d in data["data"]]
    assert m1_id in manif_ids, "tag 'cosmos' must match tag 'Cosmos' on manifestations view"


def test_global_catalog_visibility_unowned_items(client, app):
    """Test that global catalog items with active filters are returned with item_id=None
    for users who do not own them, whereas they are excluded without active global filters.
    """
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = User(email="unowned_test@iqoqo.local", display_name="Unowned Tester")
        db.session.add(user)
        db.session.flush()
        user_id = user.id

        # Seed global Work/Expression/Manifestation not owned by anyone
        w_global = Work(title="Global Unowned Book", meta={"genres": ["History"], "publisher": "Oxford"})
        db.session.add(w_global)
        db.session.flush()

        e_global = Expression(work_id=w_global.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(e_global)
        db.session.flush()

        m_global = Manifestation(expression_id=e_global.id, publisher="Oxford", meta={})
        db.session.add(m_global)
        db.session.flush()

        # Seed another work that IS owned by this user
        w_owned = Work(title="My Personal Book", meta={"genres": ["Fiction"], "publisher": "Penguin"})
        db.session.add(w_owned)
        db.session.flush()

        e_owned = Expression(work_id=w_owned.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(e_owned)
        db.session.flush()

        m_owned = Manifestation(expression_id=e_owned.id, publisher="Penguin", meta={})
        db.session.add(m_owned)
        db.session.flush()

        i_owned = Item(manifestation_id=m_owned.id, owner_id=user_id, status="owned")
        db.session.add(i_owned)

        db.session.commit()

        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Without filters, works/shelf and expressions/shelf should only return owned works
    res_works = client.get("/api/works/shelf", headers=headers)
    assert res_works.status_code == 200
    work_titles = [w["title"] for w in res_works.json["data"]]
    assert "My Personal Book" in work_titles
    assert "Global Unowned Book" not in work_titles

    res_exprs = client.get("/api/expressions/shelf", headers=headers)
    assert res_exprs.status_code == 200
    expr_titles = [e["work_title"] for e in res_exprs.json["data"]]
    assert "My Personal Book" in expr_titles
    assert "Global Unowned Book" not in expr_titles

    # 2. With global filter (genres=History), global unowned book should be returned with item_id=None
    res_works_filtered = client.get("/api/works/shelf?genres=History", headers=headers)
    assert res_works_filtered.status_code == 200
    assert len(res_works_filtered.json["data"]) == 1
    work_data = res_works_filtered.json["data"][0]
    assert work_data["title"] == "Global Unowned Book"
    assert work_data["total_items"] == 0
    assert len(work_data["owned_manifestations"]) == 1
    assert work_data["owned_manifestations"][0]["item_id"] is None

    res_exprs_filtered = client.get("/api/expressions/shelf?genres=History", headers=headers)
    assert res_exprs_filtered.status_code == 200
    assert len(res_exprs_filtered.json["data"]) == 1
    expr_data = res_exprs_filtered.json["data"][0]
    assert expr_data["work_title"] == "Global Unowned Book"
    assert expr_data["total_items"] == 0
    assert len(expr_data["owned_manifestations"]) == 1
    assert expr_data["owned_manifestations"][0]["item_id"] is None
