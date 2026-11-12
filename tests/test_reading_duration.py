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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for FRBR Item-scoped reading duration and session tracking (C115)."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, ItemStatusLog, Manifestation, User, Work, db


def _create_frbr_item(app, owner_id, status="reading", visibility="public", is_hidden=False, manifestation_id=None):
    """Create a Work/Expression/Manifestation/Item hierarchy for testing."""
    with app.app_context():
        if manifestation_id is None:
            work = Work(title=f"Reading Test Work {secrets.token_hex(4)}", meta={"authors": ["Test Author"]})
            db.session.add(work)
            db.session.flush()
            expr = Expression(work_id=work.id, content_type="text", language="en")
            db.session.add(expr)
            db.session.flush()
            man = Manifestation(expression_id=expr.id, format_type="hardcover", meta={})
            db.session.add(man)
            db.session.flush()
            manifestation_id = man.id

        item = Item(
            manifestation_id=manifestation_id,
            owner_id=owner_id,
            status=status,
            collection_status="available",
            visibility=visibility,
            is_hidden=is_hidden,
            meta={},
        )
        db.session.add(item)
        db.session.commit()
        return item.id, manifestation_id


def _create_other_user_headers(app):
    """Create a secondary user and return their Bearer auth headers and user ID."""
    with app.app_context():
        other = User(
            email=f"other-{secrets.token_hex(4)}@iqoqo.local",
            display_name="Other Reader",
            is_active=True,
        )
        other.set_password("StrongPass123!")
        db.session.add(other)
        db.session.commit()
        token = generate_internal_jwt(other)
        return {"Authorization": f"Bearer {token}"}, other.id


def test_owner_logs_reading_session_and_caps_at_200(client, app, normal_user_headers):
    """Owner can log reading sessions, updating total_minutes and capping stored entries at 200."""
    with app.app_context():
        user = db.session.execute(select(User)).scalars().first()
        assert user is not None
        owner_id = user.id

    item_id, _ = _create_frbr_item(app, owner_id, status="reading")

    # Pre-seed 200 sessions to test cap behavior
    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None
        item.meta = {
            "reading_sessions": [{"duration_minutes": 10, "logged_at": "2026-01-01T00:00:00+00:00"} for _ in range(200)],
            "total_reading_minutes": 2000,
            "reading_sessions_count": 200,
        }
        db.session.commit()

    resp = client.post(
        f"/api/items/{item_id}/reading-sessions",
        json={"duration_minutes": 45, "pages_read": 30, "note": "  Chapter 3  "},
        headers=normal_user_headers,
    )
    assert resp.status_code == 201
    summary = resp.get_json()["data"]["reading_duration_summary"]
    assert summary["total_minutes"] == 2045
    assert summary["sessions_count"] == 201

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None
        assert len(item.meta["reading_sessions"]) == 200
        assert item.meta["reading_sessions"][-1]["duration_minutes"] == 45
        assert item.meta["reading_sessions"][-1]["pages_read"] == 30
        assert item.meta["reading_sessions"][-1]["note"] == "Chapter 3"


def test_reading_session_validation_and_idor(client, app, normal_user_headers):
    """Non-owners receive 403, invalid payloads receive 400, and unauthenticated requests receive 401."""
    with app.app_context():
        user = db.session.execute(select(User)).scalars().first()
        assert user is not None
        owner_id = user.id

    item_id, _ = _create_frbr_item(app, owner_id)
    other_headers, _ = _create_other_user_headers(app)

    # Unauthenticated
    unauth = client.post(f"/api/items/{item_id}/reading-sessions", json={"duration_minutes": 30})
    assert unauth.status_code == 401

    # Non-owner IDOR
    idor = client.post(f"/api/items/{item_id}/reading-sessions", json={"duration_minutes": 30}, headers=other_headers)
    assert idor.status_code == 403

    # Non-existent item
    missing = client.post("/api/items/999999/reading-sessions", json={"duration_minutes": 30}, headers=normal_user_headers)
    assert missing.status_code == 404

    # Invalid duration (0 and > 1440)
    bad_low = client.post(f"/api/items/{item_id}/reading-sessions", json={"duration_minutes": 0}, headers=normal_user_headers)
    assert bad_low.status_code == 400

    bad_high = client.post(f"/api/items/{item_id}/reading-sessions", json={"duration_minutes": 1500}, headers=normal_user_headers)
    assert bad_high.status_code == 400


def test_item_detail_elapsed_days_and_manifestation_average(client, app, normal_user_headers):
    """GET /items/<id> computes elapsed_days from ItemStatusLog and GET /manifestations/<id> averages public logs."""
    with app.app_context():
        user = db.session.execute(select(User)).scalars().first()
        assert user is not None
        owner_id = user.id

    item1_id, man_id = _create_frbr_item(app, owner_id, status="read", visibility="public")
    _, other_id = _create_other_user_headers(app)
    item2_id, _ = _create_frbr_item(app, other_id, status="read", visibility="public", manifestation_id=man_id)
    # Private item should be excluded from manifestation average
    item3_id, _ = _create_frbr_item(app, other_id, status="read", visibility="private", is_hidden=True, manifestation_id=man_id)

    now = datetime.now(UTC)
    with app.app_context():
        db.session.add(
            ItemStatusLog(
                item_id=item1_id,
                user_id=owner_id,
                old_status="want_to_read",
                new_status="reading",
                changed_at=now - timedelta(days=5),
            )
        )
        db.session.add(
            ItemStatusLog(
                item_id=item1_id,
                user_id=owner_id,
                old_status="reading",
                new_status="read",
                changed_at=now,
            )
        )
        i1 = db.session.get(Item, item1_id)
        i2 = db.session.get(Item, item2_id)
        i3 = db.session.get(Item, item3_id)
        assert i1 is not None and i2 is not None and i3 is not None
        i1.meta = {"total_reading_minutes": 120, "reading_sessions_count": 3, "reading_sessions": []}
        i2.meta = {"total_reading_minutes": 180, "reading_sessions_count": 2, "reading_sessions": []}
        i3.meta = {"total_reading_minutes": 900, "reading_sessions_count": 10, "reading_sessions": []}
        db.session.commit()

    item_resp = client.get(f"/api/items/{item1_id}", headers=normal_user_headers)
    assert item_resp.status_code == 200
    summary = item_resp.get_json()["data"]["reading_duration_summary"]
    assert summary["total_minutes"] == 120
    assert summary["sessions_count"] == 3
    assert summary["elapsed_days"] == 5
    assert summary["started_at"] is not None
    assert summary["finished_at"] is not None

    man_resp = client.get(f"/api/manifestations/{man_id}", headers=normal_user_headers)
    assert man_resp.status_code == 200
    # Average of 120 and 180 = 150.0 (900 from hidden/private item3 excluded)
    assert man_resp.get_json()["data"]["average_reading_minutes"] == 150.0
