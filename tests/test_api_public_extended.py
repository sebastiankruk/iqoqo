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
"""Extended tests for the public API endpoints."""

import json

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, SharedCollection, User, Work, db


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email="extended@iqoqo.local", public_username="extuser", visibility="public")
        db.session.add(user)
        db.session.commit()
        return user.public_username


def test_pagination(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Pagination Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        for _ in range(15):
            item = Item(owner_id=user.id, manifestation_id=mani.id, status="read")
            db.session.add(item)
        db.session.commit()

    # Page 1
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=1")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 10
    assert data["data"]["total"] == 15
    assert data["data"]["pages"] == 2

    # Page 2
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=2")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 5


def test_shared_collection_with_status_filter(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Shared Filter Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        # 2 read, 1 wishlist
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="wish_list"))

        collection = SharedCollection(user_id=user.id, name="My Read Books", filters={"status": "read"})
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 2
    for item in data["data"]["items"]:
        assert item["status"] == "read"


def test_check_inventory_missing_query(client, test_user):
    response = client.post(f"/api/public/u/{test_user}/check", json={})
    assert response.status_code == 400
    assert "required" in json.loads(response.data)["error"]


def _make_share_headers(app, email="sharer@iqoqo.local"):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            db.session.add(user)
            db.session.commit()
        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}


def test_create_shared_collection_default_no_expiry(client, app):
    """POST /api/sharing without expires_in_days creates collection with no TTL."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "My Library"}, headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["name"] == "My Library"
    assert data.get("expires_at") is None


def test_create_shared_collection_with_expiry(client, app):
    """POST /api/sharing with valid expires_in_days sets expires_at."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Temporary Share", "expires_in_days": 7}, headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["name"] == "Temporary Share"
    assert data.get("expires_at") is not None


def test_create_shared_collection_expiry_too_low(client, app):
    """POST /api/sharing with expires_in_days < 1 returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": 0}, headers=headers)
    assert response.status_code == 400


def test_create_shared_collection_expiry_too_high(client, app):
    """POST /api/sharing with expires_in_days > 365 returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": 366}, headers=headers)
    assert response.status_code == 400


def test_create_shared_collection_expiry_non_int(client, app):
    """POST /api/sharing with non-integer expires_in_days returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": "seven"}, headers=headers)
    assert response.status_code == 400


def test_expired_shared_collection_returns_404(client, app):
    """GET /api/public/share/<expired_token> returns 404."""
    with app.app_context():
        from datetime import UTC, datetime, timedelta

        user = User(email="expired_share@iqoqo.local")
        db.session.add(user)
        db.session.flush()
        work = Work(title="Expired Shared Collection Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id)
        db.session.add(manif)
        db.session.flush()
        item = Item(owner_id=user.id, manifestation_id=manif.id, status="read")
        db.session.add(item)

        expired = SharedCollection(
            user_id=user.id,
            name="Expired Share",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.session.add(expired)
        db.session.commit()
        token = expired.share_token

    response = client.get(f"/api/public/share/{token}")
    assert response.status_code == 404


def test_active_shared_collection_returns_200(client, app):
    """GET /api/public/share/<active_token> returns 200 with items."""
    with app.app_context():
        from datetime import UTC, datetime, timedelta

        user = User(email="active_share@iqoqo.local")
        db.session.add(user)
        db.session.flush()
        work = Work(title="Active Shared Collection Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id)
        db.session.add(manif)
        db.session.flush()
        item = Item(owner_id=user.id, manifestation_id=manif.id, status="read")
        db.session.add(item)

        active = SharedCollection(
            user_id=user.id,
            name="Active Share",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.session.add(active)
        db.session.commit()
        token = active.share_token

    response = client.get(f"/api/public/share/{token}")
    assert response.status_code == 200
    assert response.json["success"] is True
