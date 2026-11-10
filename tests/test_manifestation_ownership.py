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


def test_admin_ownership_source_items_filtering(client, admin_headers, app):
    """Verify GET /api/admin/ownership/items filtering by q, wildcards, collection_status, format, and item_id."""
    with app.app_context():
        user = User(email="source_filt@iqoqo.local", display_name="Filter Source", is_active=True)
        user.set_password("pass-filt")
        db.session.add(user)
        db.session.flush()

        w1 = Work(title="Dune Special 100% Edition")
        w2 = Work(title="Neuromancer Cyber")
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type="text", language="en")
        e2 = Expression(work_id=w2.id, content_type="text", language="en")
        db.session.add_all([e1, e2])
        db.session.flush()

        m1 = Manifestation(expression_id=e1.id, isbn13="9780123456789", format="Hardcover", label="Dune Deluxe")
        m2 = Manifestation(expression_id=e2.id, isbn13="9780987654321", format="Paperback", label="Neuromancer Standard")
        db.session.add_all([m1, m2])
        db.session.flush()

        item1 = Item(
            manifestation_id=m1.id,
            owner_id=user.id,
            status="available",
            collection_status="available",
            local_barcode="DUNE_100_BC",
        )
        item2 = Item(
            manifestation_id=m2.id,
            owner_id=user.id,
            status="available",
            collection_status="lent",
            local_barcode="NEURO_001_BC",
        )
        db.session.add_all([item1, item2])
        db.session.commit()

        user_id_str = str(user.id)
        item1_id = item1.id
        item2_id = item2.id

    # 1. Without filters, returns both items
    res = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["pagination"]["total"] == 2
    item_ids = [it["id"] for it in res.json["data"]]
    assert item1_id in item_ids
    assert item2_id in item_ids

    # 2. Filter by exact item_id
    res_id = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}&item_id={item1_id}", headers=admin_headers)
    assert res_id.status_code == 200
    assert res_id.json["pagination"]["total"] == 1
    assert res_id.json["data"][0]["id"] == item1_id

    # 3. Filter by collection_status
    res_status = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}&collection_status=lent", headers=admin_headers)
    assert res_status.status_code == 200
    assert res_status.json["pagination"]["total"] == 1
    assert res_status.json["data"][0]["id"] == item2_id

    # 4. Filter by text search q (title)
    res_q = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}&q=Neuromancer", headers=admin_headers)
    assert res_q.status_code == 200
    assert res_q.json["pagination"]["total"] == 1
    assert res_q.json["data"][0]["id"] == item2_id

    # 5. Wildcard escaping in q (% metacharacter should not match everything)
    res_wildcard = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}&q=100%", headers=admin_headers)
    assert res_wildcard.status_code == 200
    assert res_wildcard.json["pagination"]["total"] == 1
    assert res_wildcard.json["data"][0]["id"] == item1_id

    # 6. Wildcard _ escaping
    res_underscore = client.get(f"/api/v1/admin/ownership/items?source_user_id={user_id_str}&q=DUNE_", headers=admin_headers)
    assert res_underscore.status_code == 200
    assert res_underscore.json["pagination"]["total"] == 1
    assert res_underscore.json["data"][0]["id"] == item1_id
