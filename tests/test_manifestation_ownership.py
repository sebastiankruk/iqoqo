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
"""Tests for FRBR Ownership facet filtering across Works, Expressions, and Manifestations."""

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

        # Work 1 (Owned): Has an owned manifestation
        work_owned = Work(title="Owned Work Alpha")
        db.session.add(work_owned)
        db.session.flush()

        expr_owned = Expression(work_id=work_owned.id, content_type="text", language="en")
        db.session.add(expr_owned)
        db.session.flush()

        m_owned = Manifestation(expression_id=expr_owned.id, isbn13="9780000000001", meta={"format": "Paperback"})
        db.session.add(m_owned)
        db.session.flush()

        item = Item(manifestation_id=m_owned.id, owner_id=user.id, status="available")
        db.session.add(item)

        # Work 2 (Not Owned): Has no owned item
        work_unowned = Work(title="Unowned Work Beta")
        db.session.add(work_unowned)
        db.session.flush()

        expr_unowned = Expression(work_id=work_unowned.id, content_type="text", language="en")
        db.session.add(expr_unowned)
        db.session.flush()

        m_not_owned = Manifestation(expression_id=expr_unowned.id, isbn13="9780000000002", meta={"format": "Hardcover"})
        db.session.add(m_not_owned)

        db.session.commit()

        token = jwt.encode({"sub": str(user.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return {
            "user_id": str(user.id),
            "headers": {"Authorization": f"Bearer {token}"},
            "owned_work_id": work_owned.id,
            "unowned_work_id": work_unowned.id,
            "owned_expr_id": expr_owned.id,
            "unowned_expr_id": expr_unowned.id,
            "owned_m_id": m_owned.id,
            "not_owned_m_id": m_not_owned.id,
        }


def test_manifestations_default_returns_both_owned_and_not_owned(client, ownership_setup):
    """By default (no ownership filter), GET /api/manifestations must return all items (both owned and unowned)."""
    resp = client.get("/api/manifestations?page=1&limit=20", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] in ids


def test_manifestations_filter_by_owned(client, ownership_setup):
    """When ownership=owned is passed, only owned manifestations are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] not in ids


def test_manifestations_filter_by_not_owned(client, ownership_setup):
    """When ownership=not_owned is passed, only unowned manifestations are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=not_owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]]
    assert ownership_setup["owned_m_id"] not in ids
    assert ownership_setup["not_owned_m_id"] in ids


def test_manifestations_filter_by_both(client, ownership_setup):
    """When ownership=owned,not_owned is passed, both are returned."""
    resp = client.get("/api/manifestations?page=1&limit=20&ownership=owned,not_owned", headers=ownership_setup["headers"])
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json["data"]]
    assert ownership_setup["owned_m_id"] in ids
    assert ownership_setup["not_owned_m_id"] in ids


def test_works_shelf_filter_by_ownership(client, ownership_setup):
    """Verify /works/shelf responds correctly to ownership filters."""
    # Default returns both
    resp_all = client.get("/api/works/shelf", headers=ownership_setup["headers"])
    assert resp_all.status_code == 200
    work_ids_all = [w["work_id"] for w in resp_all.json["data"]]
    assert ownership_setup["owned_work_id"] in work_ids_all
    assert ownership_setup["unowned_work_id"] in work_ids_all

    # Owned filter
    resp_owned = client.get("/api/works/shelf?ownership=owned", headers=ownership_setup["headers"])
    assert resp_owned.status_code == 200
    work_ids_owned = [w["work_id"] for w in resp_owned.json["data"]]
    assert ownership_setup["owned_work_id"] in work_ids_owned
    assert ownership_setup["unowned_work_id"] not in work_ids_owned

    # Not owned filter
    resp_unowned = client.get("/api/works/shelf?ownership=not_owned", headers=ownership_setup["headers"])
    assert resp_unowned.status_code == 200
    work_ids_unowned = [w["work_id"] for w in resp_unowned.json["data"]]
    assert ownership_setup["owned_work_id"] not in work_ids_unowned
    assert ownership_setup["unowned_work_id"] in work_ids_unowned


def test_expressions_shelf_filter_by_ownership(client, ownership_setup):
    """Verify /expressions/shelf responds correctly to ownership filters."""
    # Default returns both
    resp_all = client.get("/api/expressions/shelf", headers=ownership_setup["headers"])
    assert resp_all.status_code == 200
    expr_ids_all = [e["expression_id"] for e in resp_all.json["data"]]
    assert ownership_setup["owned_expr_id"] in expr_ids_all
    assert ownership_setup["unowned_expr_id"] in expr_ids_all

    # Owned filter
    resp_owned = client.get("/api/expressions/shelf?ownership=owned", headers=ownership_setup["headers"])
    assert resp_owned.status_code == 200
    expr_ids_owned = [e["expression_id"] for e in resp_owned.json["data"]]
    assert ownership_setup["owned_expr_id"] in expr_ids_owned
    assert ownership_setup["unowned_expr_id"] not in expr_ids_owned

    # Not owned filter
    resp_unowned = client.get("/api/expressions/shelf?ownership=not_owned", headers=ownership_setup["headers"])
    assert resp_unowned.status_code == 200
    expr_ids_unowned = [e["expression_id"] for e in resp_unowned.json["data"]]
    assert ownership_setup["owned_expr_id"] not in expr_ids_unowned
    assert ownership_setup["unowned_expr_id"] in expr_ids_unowned
