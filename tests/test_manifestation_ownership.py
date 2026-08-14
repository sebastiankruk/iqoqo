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
"""Tests for Manifestation ownership facet filtering."""

import jwt
import pytest

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def ownership_setup(app):
    """Seed sample works, manifestations, and user items for ownership testing."""
    with app.app_context():
        user = User(email="owner_test@example.com", display_name="Owner Tester", is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Ownership Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        # Manifestation 1: Owned by user
        m_owned = Manifestation(expression_id=expr.id, title="Owned Book", isbn13="9780000000001", meta={})
        db.session.add(m_owned)
        db.session.flush()

        item = Item(manifestation_id=m_owned.id, owner_id=user.id, status="available")
        db.session.add(item)

        # Manifestation 2: Not owned by user
        m_not_owned = Manifestation(expression_id=expr.id, title="Not Owned Book", isbn13="9780000000002", meta={})
        db.session.add(m_not_owned)

        db.session.commit()

        token = jwt.encode({"sub": str(user.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return {
            "user_id": str(user.id),
            "headers": {"Authorization": f"Bearer {token}"},
            "owned_m_id": m_owned.id,
            "not_owned_m_id": m_not_owned.id,
        }


def test_manifestations_default_returns_both_owned_and_not_owned(client, ownership_setup):
    """By default (no ownership filter), GET /api/manifestations must return all items (both owned and unowned)."""
    resp = client.get("/api/manifestations?page=1&limit=20", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]["items"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] in ids


def test_manifestations_filter_by_owned(client, ownership_setup):
    """When ownership=owned is passed, only owned manifestations are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]["items"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] not in ids


def test_manifestations_filter_by_not_owned(client, ownership_setup):
    """When ownership=not_owned is passed, only unowned manifestations are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=not_owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]["items"]]
    assert ownership_setup["owned_m_id"] not in ids
    assert ownership_setup["not_owned_m_id"] in ids


def test_manifestations_filter_by_both(client, ownership_setup):
    """When ownership=owned,not_owned is passed, both are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=owned,not_owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]["items"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] in ids
