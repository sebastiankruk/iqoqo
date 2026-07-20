# tests/test_api_status_filters.py
"""Tests for the cross-FRBR filter intersection logic for statuses."""

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
