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
"""Unit and API tests for C130 user-scoped Work reading status rollup."""

from sqlalchemy import event

from app.api.auth import generate_internal_jwt
from app.core.frbr_service import compute_work_reading_rollup
from app.db.models import Expression, Item, Manifestation, User, Work, db


def _seed_work_with_editions(title: str) -> tuple[Work, Manifestation, Manifestation]:
    work = Work(title=title, meta={"authors": ["Author Rollup"]})
    db.session.add(work)
    db.session.flush()
    expr_text = Expression(work_id=work.id, content_type="text", language="en")
    expr_audio = Expression(work_id=work.id, content_type="audiobook", language="en")
    db.session.add_all([expr_text, expr_audio])
    db.session.flush()
    m_paper = Manifestation(expression_id=expr_text.id, format_type="paperback", meta={"format": "paperback"})
    m_audio = Manifestation(expression_id=expr_audio.id, format_type="audiobook", meta={"format": "audiobook"})
    db.session.add_all([m_paper, m_audio])
    db.session.flush()
    return work, m_paper, m_audio


def test_compute_work_reading_rollup_precedence_privacy_and_batching(app):
    """Verify completed > in_progress > intent > dnf, private item inclusion, and O(1) SQL batching."""
    with app.app_context():
        user_a = User(email="rollup_a@iqoqo.local", public_username="rollupa", visibility="public")
        user_b = User(email="rollup_b@iqoqo.local", public_username="rollupb", visibility="public")
        db.session.add_all([user_a, user_b])
        db.session.flush()

        w1, w1_paper, w1_audio = _seed_work_with_editions("Rollup Completed Precedence")
        w2, w2_paper, _ = _seed_work_with_editions("Rollup In Progress")
        w3, w3_paper, w3_audio = _seed_work_with_editions("Rollup Private Item")

        # User A has both a finished audiobook and an unread paperback for W1 -> completed wins
        db.session.add(Item(owner_id=user_a.id, manifestation_id=w1_audio.id, status="listened"))
        db.session.add(Item(owner_id=user_a.id, manifestation_id=w1_paper.id, status="want_to_read"))
        # User A is actively reading W2
        db.session.add(Item(owner_id=user_a.id, manifestation_id=w2_paper.id, status="reading"))
        # User A has a private/hidden completed copy of W3, plus a DNF edition -> read wins & private counts for owner
        db.session.add(
            Item(
                owner_id=user_a.id,
                manifestation_id=w3_paper.id,
                status="read",
                visibility="private",
                is_hidden=True,
            )
        )
        db.session.add(Item(owner_id=user_a.id, manifestation_id=w3_audio.id, status="dnf"))
        db.session.commit()

        assert not hasattr(Work, "reading_status")
        assert not hasattr(Work, "work_reading_status")

        uid_a = user_a.id
        uid_b = user_b.id
        wid_list = [w1.id, w2.id, w3.id]
        w1_id, w2_id, w3_id = wid_list
        w1_audio_id = w1_audio.id
        w3_paper_id = w3_paper.id

        queries: list[str] = []

        def _capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
            queries.append(statement)

        event.listen(db.engine, "before_cursor_execute", _capture_sql)
        try:
            rollup_a = compute_work_reading_rollup(uid_a, wid_list)
        finally:
            event.remove(db.engine, "before_cursor_execute", _capture_sql)

        assert len(queries) == 1
        assert rollup_a[w1_id]["work_reading_status"] == "listened"
        assert rollup_a[w1_id]["completed_manifestation_ids"] == [w1_audio_id]
        assert rollup_a[w2_id]["work_reading_status"] == "reading"
        assert rollup_a[w2_id]["completed_manifestation_ids"] == []
        assert rollup_a[w3_id]["work_reading_status"] == "read"
        assert rollup_a[w3_id]["completed_manifestation_ids"] == [w3_paper_id]

        # Isolation: unrelated user & anonymous receive empty rollup
        assert compute_work_reading_rollup(uid_b, wid_list) == {}
        assert compute_work_reading_rollup(None, [w1_id]) == {}


def test_work_manifestation_and_shelf_rollup_endpoints(client, app):
    """Verify GET /works/<id>, GET /manifestations/<id>, and GET /works/shelf rollup & filtering."""
    with app.app_context():
        user_a = User(email="ep_rollup_a@iqoqo.local", public_username="eprollupa", visibility="public")
        user_b = User(email="ep_rollup_b@iqoqo.local", public_username="eprollupb", visibility="public")
        db.session.add_all([user_a, user_b])
        db.session.flush()

        w_read, m_paper, m_other = _seed_work_with_editions("Rollup Endpoint Read")
        w_prog, m_prog, _ = _seed_work_with_editions("Rollup Endpoint Reading")
        w_unread, _, _ = _seed_work_with_editions("Rollup Endpoint Unread")

        db.session.add(Item(owner_id=user_a.id, manifestation_id=m_paper.id, status="read"))
        db.session.add(Item(owner_id=user_a.id, manifestation_id=m_prog.id, status="reading"))
        db.session.commit()

        headers_a = {"Authorization": f"Bearer {generate_internal_jwt(user_a)}"}
        headers_b = {"Authorization": f"Bearer {generate_internal_jwt(user_b)}"}
        w_read_id = w_read.id
        w_prog_id = w_prog.id
        w_unread_id = w_unread.id
        m_paper_id = m_paper.id
        m_other_id = m_other.id

    # Work detail: authenticated owner sees 'read', unauthenticated & other user see null
    res_w_a = client.get(f"/api/works/{w_read_id}", headers=headers_a)
    assert res_w_a.status_code == 200
    assert res_w_a.json["data"]["work_reading_status"] == "read"
    assert res_w_a.json["data"]["completed_manifestation_ids"] == [m_paper_id]

    res_w_anon = client.get(f"/api/works/{w_read_id}")
    assert res_w_anon.status_code == 200
    assert res_w_anon.json["data"]["work_reading_status"] is None
    assert res_w_anon.json["data"]["completed_manifestation_ids"] == []

    res_w_b = client.get(f"/api/works/{w_read_id}", headers=headers_b)
    assert res_w_b.status_code == 200
    assert res_w_b.json["data"]["work_reading_status"] is None

    # Manifestation detail: own completed edition -> completed_via_other_edition=False; sibling -> True
    res_m_own = client.get(f"/api/manifestations/{m_paper_id}", headers=headers_a)
    assert res_m_own.status_code == 200
    assert res_m_own.json["data"]["work_reading_status"] == "read"
    assert res_m_own.json["data"]["completed_via_other_edition"] is False

    res_m_other = client.get(f"/api/manifestations/{m_other_id}", headers=headers_a)
    assert res_m_other.status_code == 200
    assert res_m_other.json["data"]["work_reading_status"] == "read"
    assert res_m_other.json["data"]["completed_via_other_edition"] is True
    assert res_m_other.json["data"]["completed_manifestation_ids"] == [m_paper_id]

    res_m_anon = client.get(f"/api/manifestations/{m_other_id}")
    assert res_m_anon.status_code == 200
    assert res_m_anon.json["data"]["work_reading_status"] is None
    assert res_m_anon.json["data"]["completed_via_other_edition"] is False

    # Shelf filtering via work_read_status
    shelf_completed = client.get("/api/works/shelf?q=Rollup+Endpoint&work_read_status=completed", headers=headers_a)
    assert shelf_completed.status_code == 200
    assert [w["work_id"] for w in shelf_completed.json["data"]] == [w_read_id]
    assert shelf_completed.json["data"][0]["work_reading_status"] == "read"

    shelf_in_prog = client.get("/api/works/shelf?q=Rollup+Endpoint&work_read_status=in_progress", headers=headers_a)
    assert shelf_in_prog.status_code == 200
    assert [w["work_id"] for w in shelf_in_prog.json["data"]] == [w_prog_id]
    assert shelf_in_prog.json["data"][0]["work_reading_status"] == "reading"

    shelf_unread = client.get("/api/works/shelf?q=Rollup+Endpoint&work_read_status=unread", headers=headers_a)
    assert shelf_unread.status_code == 200
    assert [w["work_id"] for w in shelf_unread.json["data"]] == [w_unread_id]
    assert shelf_unread.json["data"][0]["work_reading_status"] is None
