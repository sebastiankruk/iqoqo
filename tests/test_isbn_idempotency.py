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
"""Contract tests for the read-only ISBN lookup and explicit cataloging flow.

Enforces the split introduced by the REST idempotency fix: HTTP GET must be
free of side effects, while the explicit POST endpoints own FRBR entity
creation and background task scheduling.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.db.models import Expression, Item, Manifestation, User, Work, db

PROVIDER_METADATA = {
    "Title": "The Left Hand of Darkness",
    "Authors": ["Ursula K. Le Guin"],
    "Publisher": "Ace",
    "format": "paperback",
}


@pytest.fixture
def isbn_user(app):
    """A user holding the permissions required to create items."""
    with app.app_context():
        from app.api.auth import generate_internal_jwt
        from app.db.models import Permission, Role

        user = User(email="isbn_contract@example.com", display_name="ISBN Tester")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        role = Role(name="isbn_tester")
        for perm_name in ("write:item", "write:metadata"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
                db.session.flush()
            role.permissions.append(perm)
        user.roles.append(role)
        db.session.add(role)
        db.session.commit()

        return {"user_id": user.id, "headers": {"Authorization": f"Bearer {generate_internal_jwt(user)}"}}


def _row_counts() -> dict[str, int]:
    return {
        "works": db.session.execute(select(func.count()).select_from(Work)).scalar(),
        "expressions": db.session.execute(select(func.count()).select_from(Expression)).scalar(),
        "manifestations": db.session.execute(select(func.count()).select_from(Manifestation)).scalar(),
        "items": db.session.execute(select(func.count()).select_from(Item)).scalar(),
    }


# ── GET is read-only ───────────────────────────────────────────────────


def test_get_does_not_create_manifestation(client, app, isbn_user):
    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA):
        with app.app_context():
            before = _row_counts()

        resp = client.get("/api/isbn/9780441478125")

        assert resp.status_code == 200
        assert resp.get_json()["Title"] == PROVIDER_METADATA["Title"]

        with app.app_context():
            assert _row_counts() == before


def test_get_is_idempotent_across_repeated_calls(client, app, isbn_user):
    """Repeated GETs return the same payload and never mutate state."""
    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA):
        with app.app_context():
            before = _row_counts()

        payloads = [client.get("/api/isbn/9780441478125").get_json() for _ in range(3)]

        with app.app_context():
            assert _row_counts() == before

    assert all(p == payloads[0] for p in payloads)


def test_get_on_existing_manifestation_does_not_mutate(client, app, isbn_user):
    with app.app_context():
        work = Work(title="Existing", meta={"authors": ["A"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780441478125", meta={})
        db.session.add(manif)
        db.session.commit()
        before = _row_counts()
        manif_id = manif.id

    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA):
        resp = client.get("/api/isbn/9780441478125")

    assert resp.status_code == 200
    with app.app_context():
        assert _row_counts() == before
        stored = db.session.get(Manifestation, manif_id)
        # The derived Title/Authors were returned but not written back.
        assert not stored.meta or "Title" not in stored.meta


def test_get_rejects_invalid_isbn(client, app, isbn_user):
    resp = client.get("/api/isbn/not-an-isbn")
    assert resp.status_code == 400


def test_get_returns_404_when_provider_has_no_data(client, app, isbn_user):
    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=None):
        resp = client.get("/api/isbn/9780441478125")
    assert resp.status_code == 404


def test_get_does_not_leak_internal_errors(client, app, isbn_user):
    with patch("app.utils.isbn.fetch_isbn_metadata", side_effect=RuntimeError("provider exploded")):
        resp = client.get("/api/isbn/9780441478125")
    assert resp.status_code == 502
    assert "provider exploded" not in resp.get_data(as_text=True)


# ── POST performs explicit creation ────────────────────────────────────


def test_post_creates_frbr_hierarchy(client, app, isbn_user):
    with (
        patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA),
        patch("app.api.manifestations.process_fast_cover", return_value=True),
        patch("app.api.manifestations.start_cover_processing") as mock_cover,
    ):
        with app.app_context():
            before = _row_counts()

        resp = client.post(
            "/api/item/9780441478125",
            json={"Title": PROVIDER_METADATA["Title"], "Authors": PROVIDER_METADATA["Authors"]},
            headers=isbn_user["headers"],
        )

        assert resp.status_code == 200

        with app.app_context():
            after = _row_counts()
            assert after["manifestations"] == before["manifestations"] + 1
            assert after["works"] == before["works"] + 1
            assert after["expressions"] == before["expressions"] + 1
            assert after["items"] == before["items"] + 1

            manif = Manifestation.query.filter_by(isbn13="9780441478125").first()
            assert manif is not None
            assert manif.expression is not None
            assert manif.expression.work is not None
            assert manif.expression.work.title == PROVIDER_METADATA["Title"]

    mock_cover.assert_not_called()


def test_post_schedules_cover_processing_when_cover_missing(client, app, isbn_user):
    with (
        patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA),
        patch("app.api.manifestations.process_fast_cover", return_value=False),
        patch("app.api.manifestations.start_cover_processing", return_value="task-1") as mock_cover,
    ):
        resp = client.post(
            "/api/item/9780441478125",
            json={"Title": PROVIDER_METADATA["Title"]},
            headers=isbn_user["headers"],
        )

    assert resp.status_code == 200
    assert mock_cover.call_count == 1


def test_post_schedules_lod_linking(client, app, isbn_user):
    with (
        patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA),
        patch("app.api.manifestations.process_fast_cover", return_value=True),
        patch("app.core.tasks.link_manifestation_lod_task") as mock_lod,
    ):
        resp = client.post(
            "/api/item/9780441478125",
            json={"Title": PROVIDER_METADATA["Title"]},
            headers=isbn_user["headers"],
        )

    assert resp.status_code == 200
    assert mock_lod.delay.call_count == 1


def test_post_reuses_existing_manifestation(client, app, isbn_user):
    """A second POST must not duplicate the catalog entry."""
    with app.app_context():
        work = Work(title="Existing", meta={"authors": ["A"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780441478125", meta={})
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    resp = client.post("/api/item/9780441478125", json={}, headers=isbn_user["headers"])
    assert resp.status_code == 200

    with app.app_context():
        assert Manifestation.query.filter_by(isbn13="9780441478125").count() == 1
        assert db.session.get(Manifestation, manif_id) is not None


def test_post_returns_404_when_provider_has_no_metadata(client, app, isbn_user):
    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=None):
        with app.app_context():
            before = _row_counts()

        resp = client.post("/api/item/9780441478125", json={}, headers=isbn_user["headers"])

        assert resp.status_code == 404
        with app.app_context():
            assert _row_counts() == before


def test_post_rejects_invalid_isbn(client, app, isbn_user):
    resp = client.post("/api/item/not-an-isbn", json={}, headers=isbn_user["headers"])
    assert resp.status_code == 404


def test_post_requires_authentication(client, app):
    resp = client.post("/api/item/9780441478125", json={})
    assert resp.status_code in (401, 403)


# ── End-to-end: lookup then explicit cataloging ────────────────────────


def test_lookup_then_catalog_flow(client, app, isbn_user):
    """The documented flow: GET for metadata, POST to persist."""
    isbn = "9780441478125"

    # 1. Read-only lookup returns provider metadata and creates nothing.
    with patch("app.utils.isbn.fetch_isbn_metadata", return_value=PROVIDER_METADATA):
        lookup = client.get(f"/api/isbn/{isbn}")
        assert lookup.status_code == 200
        assert lookup.get_json()["Title"] == PROVIDER_METADATA["Title"]

    with app.app_context():
        assert _row_counts()["manifestations"] == 0

    # 2. The cataloging POST uses that ISBN to create the full hierarchy.
    with patch("app.api.manifestations.process_fast_cover", return_value=True):
        created = client.post(f"/api/item/{isbn}", json={}, headers=isbn_user["headers"])
    assert created.status_code == 200

    # 3. A subsequent GET now serves the local record without any provider call.
    with patch("app.utils.isbn.fetch_isbn_metadata", side_effect=AssertionError("provider must not be called")):
        local = client.get(f"/api/isbn/{isbn}")
    assert local.status_code == 200
    assert local.get_json()["Title"] == PROVIDER_METADATA["Title"]

    # 4. The item is now visible to its owner.
    with app.app_context():
        manif = Manifestation.query.filter_by(isbn13=isbn).first()
        item = Item.query.filter_by(manifestation_id=manif.id, owner_id=isbn_user["user_id"]).first()
        assert item is not None
