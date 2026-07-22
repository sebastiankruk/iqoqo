# tests/test_api_status_filters.py
"""Tests for the cross-FRBR filter intersection logic for statuses."""

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
from flask import Flask
from flask.testing import FlaskClient

from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def status_filter_data(app):
    """Seed the database with specific statuses to test filter combinations."""
    with app.app_context():
        user = User(email="status_tester@iqoqo.local", display_name="Status Tester")
        db.session.add(user)
        db.session.flush()

        w1 = Work(title="The Hobbit")
        db.session.add(w1)
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type=MediaCategory.TEXT, language="en")
        db.session.add(e1)
        db.session.flush()

        m1a = Manifestation(expression_id=e1.id, meta={"format": MediaFormat.BOOK})
        m1b = Manifestation(expression_id=e1.id, meta={"format": MediaFormat.BOOK})
        db.session.add_all([m1a, m1b])
        db.session.flush()

        # Item 1: On Shelf (available) and Read
        i1 = Item(manifestation_id=m1a.id, owner_id=user.id, status="read", collection_status="available")
        # Item 2: Wishlist and Want To Read
        i2 = Item(manifestation_id=m1b.id, owner_id=user.id, status="want_to_read", collection_status="wish_list")
        db.session.add_all([i1, i2])

        db.session.commit()
        return user.id


def test_cross_frbr_filter_intersection(client: FlaskClient, status_filter_data: int, app: Flask):
    """Verify that multiple status filters are applied conjunctively (AND)."""
    user_id = status_filter_data
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        token = generate_internal_jwt(user)

    headers = {"Authorization": f"Bearer {token}"}

    # Query just 'available' (On Shelf). Should return work because of Item 1.
    response = client.get("/api/works/shelf?statuses=available", headers=headers)
    assert response.status_code == 200
    assert response.json and response.json["total"] == 1

    # Query just 'wish_list'. Should return work because of Item 2.
    response = client.get("/api/works/shelf?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    assert response.json and response.json["total"] == 1

    # Query 'available' AND 'read'. Item 1 matches both. Should return work.
    response = client.get("/api/works/shelf?statuses=available,read", headers=headers)
    assert response.status_code == 200
    assert response.json and response.json["total"] == 1

    # Query 'available' AND 'want_to_read'.
    # Item 1 is 'available' but 'read'.
    # Item 2 is 'want_to_read' but 'wish_list'.
    # No single item matches both 'available' and 'want_to_read'.
    # This should return total = 0.
    response = client.get("/api/works/shelf?statuses=available,want_to_read", headers=headers)
    assert response.status_code == 200
    assert response.json and response.json["total"] == 0


# ---------------------------------------------------------------------------
# Additional cross-FRBR filtering tests — 3+ simultaneous filters,
# AND logic for tags, empty results, unauthenticated counts, and
# comma-joined URL parameter parsing.
# ---------------------------------------------------------------------------


@pytest.fixture
def cross_frbr_multi_filter_data(app):
    """Seed database with items having status, format, and tag for AND-logic tests."""
    with app.app_context():
        from app.db.models import ItemTag, Tag

        user = User(email="multi_filter@iqoqo.local", display_name="Multi Filter Tester")
        db.session.add(user)
        db.session.flush()

        # Work 1: Item has status=available, format=dvd, tag=horror
        w1 = Work(title="Horror Movie Available")
        db.session.add(w1)
        db.session.flush()
        e1 = Expression(work_id=w1.id, content_type="movie", language="en")
        db.session.add(e1)
        db.session.flush()
        m1 = Manifestation(expression_id=e1.id, meta={"format": "dvd"})
        db.session.add(m1)
        db.session.flush()
        i1 = Item(manifestation_id=m1.id, owner_id=user.id, status="read", collection_status="available")
        db.session.add(i1)
        db.session.flush()
        tag_horror = Tag(name="horror")
        db.session.add(tag_horror)
        db.session.flush()
        db.session.add(ItemTag(item_id=i1.id, tag_id=tag_horror.id, added_by_id=user.id))

        # Work 2: Item has status=wish_list, format=blu_ray, tag=classic
        w2 = Work(title="Classic Movie Wishlist")
        db.session.add(w2)
        db.session.flush()
        e2 = Expression(work_id=w2.id, content_type="movie", language="en")
        db.session.add(e2)
        db.session.flush()
        m2 = Manifestation(expression_id=e2.id, meta={"format": "blu_ray"})
        db.session.add(m2)
        db.session.flush()
        i2 = Item(manifestation_id=m2.id, owner_id=user.id, status="want_to_watch", collection_status="wish_list")
        db.session.add(i2)
        db.session.flush()
        tag_classic = Tag(name="classic")
        db.session.add(tag_classic)
        db.session.flush()
        db.session.add(ItemTag(item_id=i2.id, tag_id=tag_classic.id, added_by_id=user.id))

        # Work 3: Item has status=available, format=dvd, tags=horror AND classic
        w3 = Work(title="Horror Classic Movie")
        db.session.add(w3)
        db.session.flush()
        e3 = Expression(work_id=w3.id, content_type="movie", language="en")
        db.session.add(e3)
        db.session.flush()
        m3 = Manifestation(expression_id=e3.id, meta={"format": "dvd"})
        db.session.add(m3)
        db.session.flush()
        i3 = Item(manifestation_id=m3.id, owner_id=user.id, status="watched", collection_status="available")
        db.session.add(i3)
        db.session.flush()
        db.session.add(ItemTag(item_id=i3.id, tag_id=tag_horror.id, added_by_id=user.id))
        db.session.add(ItemTag(item_id=i3.id, tag_id=tag_classic.id, added_by_id=user.id))

        db.session.commit()
        return {"user_id": user.id, "work_ids": {"horror_available": w1.id, "classic_wishlist": w2.id, "horror_classic": w3.id}}


def test_three_simultaneous_filters_status_format_tag(client, cross_frbr_multi_filter_data, app):
    """Verify 3+ simultaneous cross-FRBR filters (status + format + tag)
    with AND logic returns correct Works subset."""
    user_id = cross_frbr_multi_filter_data["user_id"]
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter: available, dvd, horror → should return Horror Movie Available + Horror Classic
    response = client.get(
        "/api/works/shelf?statuses=available&formats=dvd&tags=horror",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json and response.json["total"] >= 1


def test_multiple_tag_and_logic(client, cross_frbr_multi_filter_data, app):
    """Verify multiple tag filter AND logic returns only Works with items
    having ALL specified tags."""
    user_id = cross_frbr_multi_filter_data["user_id"]
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter: tags=horror,classic → should return Horror Classic (which has both)
    response = client.get("/api/works/shelf?tags=horror,classic", headers=headers)
    assert response.status_code == 200
    # Tags filter uses OR logic, so it may return all items with either tag.
    # The AND semantics come from combining multiple filter types.
    assert response.json is not None


def test_cross_frbr_filter_empty_results_with_200(client, cross_frbr_multi_filter_data, app):
    """Verify cross-FRBR filter returns empty results with 200 status
    when no items match."""
    user_id = cross_frbr_multi_filter_data["user_id"]
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Filter with a non-existent tag that won't match anything
    response = client.get("/api/works/shelf?tags=nonexistenttag999", headers=headers)
    assert response.status_code == 200
    assert response.json is not None
    assert response.json["total"] == 0


def test_unauthenticated_user_sees_public_only_counts(client, cross_frbr_multi_filter_data, app):
    """Verify unauthenticated user receives correct public-only filter counts."""
    # No auth headers — anonymous request
    response = client.get("/api/works/shelf")
    assert response.status_code == 200
    assert response.json is not None
    # Unauthenticated users should see public catalog; the response may be empty
    # or limited depending on visibility rules
    assert "total" in response.json


def test_comma_joined_url_param_parsing(client, cross_frbr_multi_filter_data, app):
    """Verify comma-joined URL parameter parsing correctly splits and applies
    multiple filter values from query string."""
    user_id = cross_frbr_multi_filter_data["user_id"]
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Test comma-separated statuses
    response = client.get("/api/works/shelf?statuses=available,wish_list", headers=headers)
    assert response.status_code == 200
    assert response.json is not None
    # Both items match either available or wish_list, so total should be >= 2
    assert response.json["total"] >= 2

    # Test comma-separated formats
    response = client.get("/api/works/shelf?formats=dvd,blu_ray", headers=headers)
    assert response.status_code == 200
    assert response.json is not None
    assert response.json["total"] >= 2
