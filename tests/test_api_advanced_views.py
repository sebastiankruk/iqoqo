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

import pytest

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, User, Work, db


def _is_sqlite(app):
    return "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", "")


def _requires_postgresql():
    """Skip test if running on SQLite (JSONB functions not supported)."""
    import os
    return os.environ.get("DATABASE_URL", "").startswith("sqlite")


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

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT)
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
            meta={
                "tags": ["fantasy", "epic"],
                "genres": ["High Fantasy"],
                "publisher": "Allen & Unwin"
            }
        )
        i2 = Item(
            manifestation_id=m1b.id,
            owner_id=user.id,
            status="want_to_read",
            meta={
                "tags": ["favorite", "fantasy"],
                "collections": ["My Precious"],
                "publisher": "HarperCollins"
            }
        )
        db.session.add_all([i1, i2])

        db.session.commit()
        return user.id


@pytest.mark.skipif(_requires_postgresql(), reason="JSONB functions require PostgreSQL")
def test_get_taxonomies_extraction(client, complex_shelf_data, app):
    """Test GET /api/taxonomies extracts and deduplicates JSONB arrays correctly."""
    user_id = complex_shelf_data
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/taxonomies", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    assert "epic" in data["tags"]
    assert "fantasy" in data["tags"]
    assert "favorite" in data["tags"]
    assert len(data["tags"]) == 3

    assert "High Fantasy" in data["genres"]
    assert "My Precious" in data["collections"]

    assert "Allen & Unwin" in data["publishers"]
    assert "HarperCollins" in data["publishers"]


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


def test_unauthorized_access_blocked(client):
    """Ensure taxonomy and work routes enforce authentication."""
    res1 = client.get("/api/taxonomies")
    assert res1.status_code == 401

    res2 = client.get("/api/works/shelf")
    assert res2.status_code == 401


@pytest.mark.skipif(_requires_postgresql(), reason="JSONB functions require PostgreSQL")
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


@pytest.mark.skipif(_requires_postgresql(), reason="JSONB functions require PostgreSQL")
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
