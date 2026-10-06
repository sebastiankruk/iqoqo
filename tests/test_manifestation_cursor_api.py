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
"""API tests for keyset cursor pagination on GET /api/manifestations.

Covers multi-page cursor traversal, backward-compatible offset pagination,
and HTTP 400 handling of malformed / out-of-range cursors.
"""

import base64
import json

import jwt
import pytest

from app.db.models import Expression, Manifestation, User, Work, db
from app.utils.pagination import encode_manifestation_cursor, encode_start_cursor

#: Sentinel token requesting the first keyset page (no lower bound).
START = encode_start_cursor()


@pytest.fixture
def cursor_setup(app):
    """Seed 25 manifestations in a known, monotonically increasing id order."""
    with app.app_context():
        user = User(email="cursor_test@example.com", display_name="Cursor Tester", is_active=True)
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Cursor Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        for i in range(25):
            db.session.add(Manifestation(expression_id=expr.id, isbn13=f"97800000{i:04d}", meta={"format": "book"}))

        db.session.commit()

        token = jwt.encode({"sub": str(user.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return {"headers": {"Authorization": f"Bearer {token}"}}


# ── Forward traversal ──────────────────────────────────────────────────


def test_initial_page_returns_cursor(client, cursor_setup):
    """A first keyset request is expressed as the start sentinel cursor."""
    resp = client.get(f"/api/manifestations?cursor={START}&limit=10", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["data"]) == 10
    assert body["meta"]["next_cursor"]
    assert body["meta"]["has_more"] is True


def test_empty_cursor_string_is_rejected(client, cursor_setup):
    """`cursor=` with no token is a client bug, not a request for page one."""
    resp = client.get("/api/manifestations?cursor=&limit=10", headers=cursor_setup["headers"])
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_first_keyset_page_can_be_requested_without_cursor(client, cursor_setup):
    """Omitting `cursor` entirely keeps the offset contract (see below)."""
    resp = client.get("/api/manifestations?limit=10", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["next_cursor"] is None


def test_cursor_traversal_visits_every_manifestation_exactly_once(client, cursor_setup):
    seen: list[int] = []
    pages = 0
    cursor: str | None = START

    while cursor is not None:
        resp = client.get(f"/api/manifestations?limit=10&cursor={cursor}", headers=cursor_setup["headers"])
        assert resp.status_code == 200
        body = resp.get_json()
        seen.extend(m["id"] for m in body["data"])
        cursor = body["meta"]["next_cursor"]
        pages += 1
        assert pages < 20, "cursor traversal failed to terminate"

    assert pages == 3, f"expected 3 pages for 25 rows at limit=10, got {pages}"
    assert len(seen) == 25
    assert len(set(seen)) == 25, "cursor pagination returned duplicate rows"
    # Catalog is ordered newest-first by id.
    assert seen == sorted(seen, reverse=True)


def test_last_page_has_no_next_cursor(client, cursor_setup):
    resp = client.get(f"/api/manifestations?limit=25&cursor={START}", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["data"]) == 25
    assert body["meta"]["has_more"] is False
    assert body["meta"]["next_cursor"] is None


def test_cursor_past_end_returns_empty_page(client, cursor_setup):
    """A valid cursor beyond the newest row yields an empty page, not an error."""
    resp = client.get(f"/api/manifestations?limit=10&cursor={encode_manifestation_cursor(1)}", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"] == []
    assert body["meta"]["next_cursor"] is None


def test_cursor_respects_filters(client, cursor_setup):
    resp = client.get(f"/api/manifestations?limit=10&cursor={START}&format=book", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 10


def test_cursor_page_size_is_capped(client, cursor_setup):
    resp = client.get(f"/api/manifestations?cursor={START}&limit=100000", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["limit"] == 100


# ── Backward compatibility ─────────────────────────────────────────────


def test_offset_pagination_still_works(client, cursor_setup):
    resp = client.get("/api/manifestations?page=2&limit=10", headers=cursor_setup["headers"])
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["page"] == 2
    assert body["meta"]["total"] == 25
    assert body["meta"]["pages"] == 3
    assert len(body["data"]) == 10


def test_offset_pages_do_not_overlap_with_each_other(client, cursor_setup):
    p1 = client.get("/api/manifestations?page=1&limit=10", headers=cursor_setup["headers"]).get_json()["data"]
    p2 = client.get("/api/manifestations?page=2&limit=10", headers=cursor_setup["headers"]).get_json()["data"]
    assert not ({m["id"] for m in p1} & {m["id"] for m in p2})


def test_default_request_uses_offset_mode(client, cursor_setup):
    resp = client.get("/api/manifestations", headers=cursor_setup["headers"])
    body = resp.get_json()
    assert "total" in body["meta"]
    assert body["meta"]["page"] == 1


# ── Malformed / out-of-range cursor handling (HTTP 400) ────────────────


@pytest.mark.parametrize(
    "cursor",
    [
        "!!!not-base64!!!",
        "%%%%",
        "a",
        "e30",  # base64 for "{}" - valid base64, invalid payload
    ],
)
def test_malformed_cursor_returns_400(client, cursor_setup, cursor):
    resp = client.get(f"/api/manifestations?cursor={cursor}", headers=cursor_setup["headers"])
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_cursor_with_non_integer_id_returns_400(client, cursor_setup):
    token = base64.urlsafe_b64encode(json.dumps({"v": 1, "id": "abc"}).encode()).decode().rstrip("=")
    resp = client.get(f"/api/manifestations?cursor={token}", headers=cursor_setup["headers"])
    assert resp.status_code == 400


def test_cursor_with_out_of_range_id_returns_400(client, cursor_setup):
    """Negative / zero ids are structurally invalid, not merely empty pages."""
    from app.utils.pagination import encode_manifestation_cursor

    resp = client.get(f"/api/manifestations?cursor={encode_manifestation_cursor(-5)}", headers=cursor_setup["headers"])
    assert resp.status_code == 400


def test_cursor_with_unsupported_version_returns_400(client, cursor_setup):
    token = base64.urlsafe_b64encode(json.dumps({"v": 99, "id": 5}).encode()).decode().rstrip("=")
    resp = client.get(f"/api/manifestations?cursor={token}", headers=cursor_setup["headers"])
    assert resp.status_code == 400


def test_oversized_cursor_returns_400(client, cursor_setup):
    resp = client.get(f"/api/manifestations?cursor={'A' * 600}", headers=cursor_setup["headers"])
    assert resp.status_code == 400


def test_cursor_with_search_returns_400(client, cursor_setup):
    """A monotonic id cursor is meaningless in a relevance-ranked result set."""
    resp = client.get(f"/api/manifestations?q=work&cursor={START}", headers=cursor_setup["headers"])
    assert resp.status_code == 400
    assert "full-text search" in resp.get_json()["error"]


def test_error_response_does_not_reflect_raw_cursor(client, cursor_setup):
    """Error text reaches clients; it must not echo the attacker's payload."""
    secret = "SECRETVALUE"
    resp = client.get(f"/api/manifestations?cursor={secret}", headers=cursor_setup["headers"])
    assert resp.status_code == 400
    assert secret not in json.dumps(resp.get_json())
