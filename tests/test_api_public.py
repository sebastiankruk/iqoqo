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
"""Tests for the public API endpoints."""

import json

import pytest

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def public_user(app):
    with app.app_context():
        user = User(
            email="public@iqoqo.local", display_name="Public User", public_username="publicuser", visibility="public", bio="Cave man bio"
        )
        db.session.add(user)
        db.session.commit()
        return user.public_username


@pytest.fixture
def sample_data(app, public_user):
    with app.app_context():
        user = User.query.filter_by(public_username=public_user).first()
        # Create FRBR chain
        work = Work(title="The Cave Bible", meta={"authors": ["Old Man"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, isbn13="9780000000001", publisher="Rock Press")
        db.session.add(mani)
        db.session.flush()

        # Public item
        item1 = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False)
        db.session.add(item1)

        # Hidden item
        item2 = Item(owner_id=user.id, manifestation_id=mani.id, status="want_to_read", is_hidden=True)
        db.session.add(item2)

        db.session.commit()
        return True


def test_get_public_profile(client, public_user, sample_data):
    response = client.get(f"/api/public/u/{public_user}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["data"]["username"] == "publicuser"
    assert data["data"]["public_item_count"] == 1  # item2 is hidden


def test_get_public_profile_not_found(client):
    response = client.get("/api/public/u/nonexistent")
    assert response.status_code == 404


def test_get_public_items(client, public_user, sample_data):
    response = client.get(f"/api/public/u/{public_user}/items")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["status"] == "read"


def test_check_inventory_found(client, public_user, sample_data):
    response = client.post(f"/api/public/u/{public_user}/check", json={"query": "9780000000001"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["data"]) > 0
    assert data["data"][0]["type"] == "item"
    assert data["data"][0]["title"] == "The Cave Bible"


def test_check_inventory_by_title(client, public_user, sample_data):
    response = client.post(f"/api/public/u/{public_user}/check", json={"query": "Cave Bible"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["data"]) > 0


def test_check_inventory_manifestation_only(client, public_user, sample_data, app):
    with app.app_context():
        # Add another manifestation no one owns
        expr = Expression.query.first()
        mani2 = Manifestation(expression_id=expr.id, isbn13="9780000000002", publisher="Unowned Press")
        db.session.add(mani2)
        db.session.commit()

    response = client.post(f"/api/public/u/{public_user}/check", json={"query": "9780000000002"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["data"]) > 0
    assert data["data"][0]["type"] == "manifestation"
    assert data["data"][0]["title"] == "The Cave Bible"


def test_get_public_work_content_negotiation_html(client, sample_data):
    work = Work.query.filter_by(title="The Cave Bible").first()
    assert work is not None
    # Client asks for text/html without format arg
    response = client.get(
        f"/api/public/works/{work.id}",
        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    assert response.status_code == 303
    assert response.headers["Location"] == f"/work/{work.id}"


def test_get_public_manifestation_content_negotiation_html(client, sample_data):
    mani = Manifestation.query.first()
    assert mani is not None
    response = client.get(
        f"/api/public/manifestations/{mani.id}",
        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    assert response.status_code == 303
    assert response.headers["Location"] == f"/manifestation/{mani.id}"


def test_get_work_detail_endpoint(client, sample_data):
    work = Work.query.filter_by(title="The Cave Bible").first()
    assert work is not None
    response = client.get(f"/api/works/{work.id}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["data"]["id"] == work.id
    assert data["data"]["title"] == "The Cave Bible"
    assert len(data["data"]["expressions"]) >= 1
    expr = data["data"]["expressions"][0]
    assert len(expr["manifestations"]) >= 1
    assert expr["manifestations"][0]["publisher"] == "Rock Press"


def test_get_expression_detail_endpoint(client, sample_data):
    expr = Expression.query.first()
    assert expr is not None
    response = client.get(f"/api/expressions/{expr.id}")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["data"]["id"] == expr.id
    assert data["data"]["work_title"] == "The Cave Bible"
    assert len(data["data"]["manifestations"]) >= 1


def test_sitemap_includes_works(client, sample_data):
    work = Work.query.filter_by(title="The Cave Bible").first()
    assert work is not None
    response = client.get("/api/public/sitemap.xml")
    assert response.status_code == 200
    xml = response.data.decode("utf-8")
    assert f"/work/{work.id}" in xml
    assert "/manifestation/" in xml
