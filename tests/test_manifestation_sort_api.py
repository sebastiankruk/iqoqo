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
"""Tests for manifestation sorting by recently added/updated copy and title."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def sort_setup(app):
    """Create two manifestations where the older manifestation has a newer user copy."""
    with app.app_context():
        user = User(email="sort_test@example.com", display_name="Sort Tester", is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        w_old = Work(title="Zebra Album")
        w_new = Work(title="Alpha Book")
        db.session.add_all([w_old, w_new])
        db.session.flush()

        e_old = Expression(work_id=w_old.id, content_type="music", language="en")
        e_new = Expression(work_id=w_new.id, content_type="text", language="en")
        db.session.add_all([e_old, e_new])
        db.session.flush()

        # Older manifestation (lower ID)
        m_old = Manifestation(expression_id=e_old.id, meta={"format": "cd"})
        # Newer manifestation (higher ID, no copy owned by user)
        m_new = Manifestation(expression_id=e_new.id, meta={"format": "book"})
        db.session.add_all([m_old, m_new])
        db.session.flush()

        # User adds a copy of the older manifestation
        now = datetime.now(UTC)
        item = Item(
            manifestation_id=m_old.id,
            owner_id=user.id,
            status="available",
            added_at=now,
            updated_at=now + timedelta(seconds=5),
        )
        db.session.add(item)
        db.session.commit()

        token = jwt.encode({"sub": str(user.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "m_old_id": m_old.id,
            "m_new_id": m_new.id,
        }


def test_get_manifestations_defaults_to_recently_added_copy_for_auth_user(client, sort_setup):
    """Older manifestation with a newly added user copy ranks before newer unowned manifestations."""
    res = client.get("/api/manifestations?page=1&limit=20", headers=sort_setup["headers"])
    assert res.status_code == 200
    ids = [entry["id"] for entry in res.get_json()["data"]]
    assert ids.index(sort_setup["m_old_id"]) < ids.index(sort_setup["m_new_id"])


def test_get_manifestations_anonymous_defaults_to_id_desc(client, sort_setup):
    """Anonymous callers keep descending manifestation ID order."""
    res = client.get("/api/manifestations?page=1&limit=20")
    assert res.status_code == 200
    ids = [entry["id"] for entry in res.get_json()["data"]]
    assert ids.index(sort_setup["m_new_id"]) < ids.index(sort_setup["m_old_id"])


def test_get_manifestations_sort_by_title(client, sort_setup):
    """Explicit sort=title / sort=title-desc orders by Work.title."""
    res_asc = client.get("/api/manifestations?page=1&limit=20&sort=title", headers=sort_setup["headers"])
    assert res_asc.status_code == 200
    ids_asc = [entry["id"] for entry in res_asc.get_json()["data"]]
    assert ids_asc.index(sort_setup["m_new_id"]) < ids_asc.index(sort_setup["m_old_id"])

    res_desc = client.get("/api/manifestations?page=1&limit=20&sort=title-desc", headers=sort_setup["headers"])
    assert res_desc.status_code == 200
    ids_desc = [entry["id"] for entry in res_desc.get_json()["data"]]
    assert ids_desc.index(sort_setup["m_old_id"]) < ids_desc.index(sort_setup["m_new_id"])


def test_get_recent_manifestations_ranks_recently_added_copy_first(client, sort_setup):
    """Dashboard /manifestations/recent bubbles recently added copies to the top."""
    res = client.get("/api/manifestations/recent?limit=10", headers=sort_setup["headers"])
    assert res.status_code == 200
    ids = [entry["id"] for entry in res.get_json()["data"]]
    assert ids.index(sort_setup["m_old_id"]) < ids.index(sort_setup["m_new_id"])


def test_get_manifestations_search_query_does_not_collide_with_browse_sort(client, sort_setup):
    """FTS search (?q=...) must not fall through into the browse-only sort/cursor block."""
    res = client.get("/api/manifestations?page=1&limit=20&q=Alpha", headers=sort_setup["headers"])
    assert res.status_code == 200
    ids = [entry["id"] for entry in res.get_json()["data"]]
    assert sort_setup["m_new_id"] in ids
