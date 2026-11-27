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
"""Tests for anonymized manifestation reading stats, popularity timeline, and cover images privacy (C158)."""

from datetime import UTC, datetime, timedelta

from app.db.core import ImageScan, ItemStatusLog
from app.db.models import Expression, Item, Manifestation, User, Work, db


def _seed_manifestation_activity(app):
    """Create a manifestation with public, private, and hidden items plus status logs and images."""
    with app.app_context():
        user1 = User(email="reader1@example.com", display_name="Reader One", is_active=True)
        user1.set_password("Pass123!")
        user2 = User(email="reader2@example.com", display_name="Reader Two", is_active=True)
        user2.set_password("Pass123!")
        db.session.add_all([user1, user2])
        db.session.flush()

        work = Work(title="Solaris")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id, meta={"format": "book"})
        empty_man = Manifestation(expression_id=expr.id, meta={"format": "ebook"})
        db.session.add_all([man, empty_man])
        db.session.flush()

        t_start = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
        t_end = t_start + timedelta(days=5)

        # Public completed item
        item_pub_done = Item(
            manifestation_id=man.id,
            owner_id=user1.id,
            status="read",
            visibility="public",
            is_hidden=False,
            added_at=t_start,
            meta={"total_reading_minutes": 120, "notes": "SUPER_SECRET_USER_NOTE"},
        )
        # Public currently reading item
        item_pub_reading = Item(
            manifestation_id=man.id,
            owner_id=user2.id,
            status="reading",
            visibility="public",
            is_hidden=False,
            added_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            meta={"total_reading_minutes": 60},
        )
        # Private item (must be excluded from public stats)
        item_private = Item(
            manifestation_id=man.id,
            owner_id=user2.id,
            status="read",
            visibility="private",
            added_at=t_start,
            meta={"total_reading_minutes": 999, "notes": "PRIVATE_NOTE_DO_NOT_LEAK"},
        )
        # Hidden item (must be excluded)
        item_hidden = Item(
            manifestation_id=man.id,
            owner_id=user1.id,
            status="read",
            is_hidden=True,
            added_at=t_start,
            meta={"total_reading_minutes": 500},
        )
        db.session.add_all([item_pub_done, item_pub_reading, item_private, item_hidden])
        db.session.flush()

        db.session.add_all(
            [
                ItemStatusLog(item_id=item_pub_done.id, user_id=user1.id, new_status="reading", changed_at=t_start),
                ItemStatusLog(item_id=item_pub_done.id, user_id=user1.id, new_status="read", changed_at=t_end),
                ItemStatusLog(item_id=item_private.id, user_id=user2.id, new_status="reading", changed_at=t_start),
                ItemStatusLog(item_id=item_private.id, user_id=user2.id, new_status="read", changed_at=t_start + timedelta(days=40)),
            ]
        )

        img = ImageScan(
            manifestation_id=man.id,
            file_path="https://example.org/alt-cover.jpg",
            scan_type="back",
            source="community",
        )
        db.session.add(img)
        db.session.commit()
        return {"man_id": man.id, "empty_man_id": empty_man.id}


def test_manifestation_stats_accuracy_and_privacy(client, app):
    """GET /api/manifestations/<id>/stats aggregates only public non-hidden items with zero PII/notes."""
    ids = _seed_manifestation_activity(app)
    resp = client.get(f"/api/manifestations/{ids['man_id']}/stats")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    data = payload["data"]

    assert data["manifestation_id"] == ids["man_id"]
    assert data["total_items"] == 2
    assert data["reader_count"] == 2
    assert data["completed_count"] == 1
    assert data["avg_session_minutes"] == 90.0
    assert data["avg_reading_days"] == 5.0

    buckets = {b["month"]: b for b in data["popularity_over_time"]}
    assert buckets["2026-02"] == {"month": "2026-02", "added_count": 1, "completed_count": 1}
    assert buckets["2026-03"] == {"month": "2026-03", "added_count": 1, "completed_count": 0}

    serialized = resp.get_data(as_text=True)
    assert "SUPER_SECRET_USER_NOTE" not in serialized
    assert "PRIVATE_NOTE_DO_NOT_LEAK" not in serialized
    assert "reader1@example.com" not in serialized
    assert "owner_id" not in serialized


def test_manifestation_stats_empty_and_not_found(client, app):
    """Zero-activity manifestations return 200 empty stats; missing IDs return 404."""
    ids = _seed_manifestation_activity(app)
    empty_resp = client.get(f"/api/manifestations/{ids['empty_man_id']}/stats")
    assert empty_resp.status_code == 200
    empty_payload = empty_resp.get_json()
    assert empty_payload["success"] is True
    empty_data = empty_payload["data"]
    assert empty_data == {
        "manifestation_id": ids["empty_man_id"],
        "total_items": 0,
        "reader_count": 0,
        "completed_count": 0,
        "avg_session_minutes": None,
        "avg_reading_days": None,
        "popularity_over_time": [],
    }

    missing_resp = client.get("/api/manifestations/999999/stats")
    assert missing_resp.status_code == 404


def test_manifestation_images_omits_uploader_identity(client, app):
    """GET /api/manifestations/<id>/images exposes F3 cover provenance without uploader PII."""
    ids = _seed_manifestation_activity(app)
    resp = client.get(f"/api/manifestations/{ids['man_id']}/images")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    images = payload["data"]
    assert len(images) == 1
    assert images[0]["url"] == "https://example.org/alt-cover.jpg"
    assert images[0]["label"] == "back"
    assert images[0]["source"] == "community"
    assert "user_id" not in images[0]
    assert "owner_id" not in images[0]
    assert "email" not in images[0]

    empty_img_resp = client.get(f"/api/manifestations/{ids['empty_man_id']}/images")
    assert empty_img_resp.status_code == 200
    assert empty_img_resp.get_json()["data"] == []


def test_manifestation_stats_friends_only_exclusion_media_statuses_and_12_month_cap(client, app):
    """Stats exclude friends_only copies, count non-book completion statuses, and cap timeline at 12 months."""
    with app.app_context():
        u = User(email="media_stats@example.com", display_name="Media Fan", is_active=True)
        u.set_password("Pass123!")
        db.session.add(u)
        db.session.flush()

        w = Work(title="Multi-Media Concert")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="video", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, meta={"format": "blu-ray"})
        db.session.add(m)
        db.session.flush()

        # Friends-only item must be excluded from public stats
        db.session.add(Item(manifestation_id=m.id, owner_id=u.id, status="watched", visibility="friends_only"))
        # 14 months of public items across non-book statuses
        statuses = ["watched", "listened", "played", "built", "watching", "listening", "playing"]
        base_dt = datetime(2025, 1, 15, tzinfo=UTC)
        for idx in range(14):
            month_dt = datetime(2025 + (idx // 12), (idx % 12) + 1, 15, tzinfo=UTC)
            db.session.add(
                Item(
                    manifestation_id=m.id,
                    owner_id=u.id,
                    status=statuses[idx % len(statuses)],
                    visibility="public",
                    added_at=month_dt if month_dt >= base_dt else base_dt,
                )
            )
        db.session.commit()
        man_id = m.id

    resp = client.get(f"/api/manifestations/{man_id}/stats")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total_items"] == 14
    assert data["reader_count"] == 14
    assert data["completed_count"] == 8
    assert len(data["popularity_over_time"]) == 12
    assert data["popularity_over_time"][0]["month"] == "2025-03"
    assert data["popularity_over_time"][-1]["month"] == "2026-02"


def test_manifestation_stats_ignores_malformed_reading_minutes_without_500(client, app):
    """Non-integer or overflowing Item.meta['total_reading_minutes'] values return NULL safely without HTTP 500."""
    from sqlalchemy.dialects import postgresql

    from app.api.manifestations import _safe_total_reading_minutes_expr

    compiled = _safe_total_reading_minutes_expr("postgresql").compile(dialect=postgresql.dialect())
    pg_sql = str(compiled)
    assert "CASE WHEN" in pg_sql
    assert "~" in pg_sql
    assert "AS INTEGER)" in pg_sql
    assert "^[0-9]{1,9}$" in compiled.params.values()

    with app.app_context():
        u = User(email="dirty_meta_stats@example.com", display_name="Edge Reader", is_active=True)
        u.set_password("Pass123!")
        db.session.add(u)
        db.session.flush()

        w = Work(title="Malformed Duration Case")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, meta={"format": "book"})
        db.session.add(m)
        db.session.flush()

        raw_values = [120, "60", "45.5", "bad", "", "-5", "99999999999999999", 45.5]
        for val in raw_values:
            db.session.add(
                Item(
                    manifestation_id=m.id,
                    owner_id=u.id,
                    status="read",
                    visibility="public",
                    is_hidden=False,
                    meta={"total_reading_minutes": val},
                )
            )
        db.session.commit()
        man_id = m.id

    detail_resp = client.get(f"/api/manifestations/{man_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["data"]["average_reading_minutes"] == 90.0

    stats_resp = client.get(f"/api/manifestations/{man_id}/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json()["data"]
    assert stats_data["total_items"] == 8
    assert stats_data["avg_session_minutes"] == 90.0


def test_manifestation_stats_computes_non_book_avg_reading_days(client, app):
    """avg_reading_days covers listening, watching, playing, and building start statuses."""
    with app.app_context():
        u = User(email="nonbook_days@example.com", display_name="Game Collector", is_active=True)
        u.set_password("Pass123!")
        db.session.add(u)
        db.session.flush()

        w = Work(title="Multi-Format Campaign")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="board_game", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, meta={"format": "board_game"})
        db.session.add(m)
        db.session.flush()

        pairs = [
            ("listening", "listened", 2),
            ("watching", "watched", 4),
            ("playing", "played", 6),
            ("building", "built", 8),
        ]
        base = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        for idx, (start_st, done_st, days) in enumerate(pairs):
            item = Item(
                manifestation_id=m.id,
                owner_id=u.id,
                status=done_st,
                visibility="public",
                is_hidden=False,
                added_at=base + timedelta(days=idx),
            )
            db.session.add(item)
            db.session.flush()
            db.session.add_all(
                [
                    ItemStatusLog(item_id=item.id, user_id=u.id, new_status=start_st, changed_at=base),
                    ItemStatusLog(item_id=item.id, user_id=u.id, new_status=done_st, changed_at=base + timedelta(days=days)),
                ]
            )
        db.session.commit()
        man_id = m.id

    resp = client.get(f"/api/manifestations/{man_id}/stats")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["reader_count"] == 4
    assert data["completed_count"] == 4
    assert data["avg_reading_days"] == 5.0
