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

"""Tests for admin API endpoints — FRBR search permission gating."""

import pytest

from app.api.auth import generate_internal_jwt
from app.core.permissions import PermissionName
from app.db import db
from app.db.models import Expression, Manifestation, Permission, Role, User, Work


@pytest.fixture
def frbr_search_setup(app):
    """Seed database with users, roles, and FRBR hierarchy for FRBR search tests."""
    with app.app_context():
        # Ensure read:metadata permission exists
        read_perm = Permission.query.filter_by(name=PermissionName.READ_METADATA).first()
        if not read_perm:
            read_perm = Permission(name=PermissionName.READ_METADATA)
            db.session.add(read_perm)

        # Create custodian role with read:metadata
        custodian_role = Role.query.filter_by(name="custodian").first()
        if not custodian_role:
            custodian_role = Role(name="custodian")
            db.session.add(custodian_role)
        if read_perm not in custodian_role.permissions:
            custodian_role.permissions.append(read_perm)

        # Create a user with the custodian role (has read:metadata, but NOT admin)
        u_custodian = User(email="cust_meta@iqoqo.local", display_name="Cust Metadata", public_username="cust_meta")
        u_custodian.roles.append(custodian_role)
        db.session.add(u_custodian)

        # Create a plain user with no special permissions
        u_plain = User(email="plain_meta@iqoqo.local", display_name="Plain Meta", public_username="plain_meta")
        db.session.add(u_plain)

        # Create FRBR hierarchy for searchable data
        work = Work(title="Searchable Test Work", meta={"authors": ["Test Author"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780000000001", meta={})
        db.session.add(manif)
        db.session.commit()

        custodian_token = generate_internal_jwt(u_custodian)
        plain_token = generate_internal_jwt(u_plain)

        return {
            "custodian_headers": {"Authorization": f"Bearer {custodian_token}"},
            "plain_headers": {"Authorization": f"Bearer {plain_token}"},
            "work_id": work.id,
        }


def test_frbr_search_by_custodian_with_read_metadata(client, frbr_search_setup):
    """Verify a user with read:metadata (but NOT admin role) can search FRBR entities."""
    headers = frbr_search_setup["custodian_headers"]

    resp = client.get("/api/v1/admin/frbr/search?q=Searchable", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
    body = resp.get_json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_frbr_search_by_plain_user_without_read_metadata(client, frbr_search_setup):
    """Verify a user without read:metadata permission gets 403 on FRBR search."""
    headers = frbr_search_setup["plain_headers"]

    resp = client.get("/api/v1/admin/frbr/search?q=Searchable", headers=headers)
    assert resp.status_code == 403


# ── Custodian (non-admin) permission enforcement tests ────────────────────


def test_custodian_can_update_work(client, admin_headers, custodian_headers, app):
    """Custodian (with write:metadata, NOT admin) can PUT work FRBR endpoint."""
    with app.app_context():
        work = Work(title="Custodian Test Work")
        db.session.add(work)
        db.session.commit()
        work_id = work.id

    resp = client.put(
        f"/api/v1/admin/frbr/work/{work_id}",
        json={"title": "Updated by Custodian"},
        headers=custodian_headers,
    )
    assert resp.status_code == 200


def test_read_metadata_user_cannot_update_work(client, normal_user_headers, app):
    """User with only read:metadata (via normal_user) cannot PUT work — expects 403."""
    with app.app_context():
        work = Work(title="Forbidden Test Work")
        db.session.add(work)
        db.session.commit()
        work_id = work.id

    resp = client.put(
        f"/api/v1/admin/frbr/work/{work_id}",
        json={"title": "Should Fail"},
        headers=normal_user_headers,
    )
    # normal_user has write:item, but not write:metadata — should be forbidden
    assert resp.status_code == 403


def test_custodian_can_update_manifestation(client, custodian_headers, app):
    """Custodian (write:metadata, NOT admin) can PUT manifestation FRBR endpoint."""
    with app.app_context():
        work = Work(title="Custodian Manif Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000100", meta={})
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    resp = client.put(
        f"/api/v1/admin/frbr/manifestation/{manif_id}",
        json={"publisher": "Custodian Publisher"},
        headers=custodian_headers,
    )
    assert resp.status_code == 200


def test_custodian_can_add_work_part(client, custodian_headers, app):
    """Custodian (write:metadata, NOT admin) can POST add work part."""
    with app.app_context():
        w1 = Work(title="Container Work")
        w2 = Work(title="Part Work")
        db.session.add_all([w1, w2])
        db.session.commit()
        w1_id = w1.id
        w2_id = w2.id

    resp = client.post(
        f"/api/works/{w1_id}/parts",
        json={"part_work_id": w2_id, "sequence": 1},
        headers=custodian_headers,
    )
    assert resp.status_code == 200


def test_custodian_with_read_metadata_can_access_frbr_tree(client, custodian_headers, app):
    """Non-admin with read:metadata can access FRBR tree endpoint."""
    with app.app_context():
        work = Work(title="FRBR Tree Custodian Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000200", meta={})
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    resp = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=custodian_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["manifestation"]["id"] == manif_id


def test_user_without_read_metadata_cannot_access_frbr_tree(client, normal_user_headers, app):
    """User without read:metadata gets 403 on FRBR tree endpoint."""
    resp = client.get("/api/v1/admin/frbr/tree/manifestation/1", headers=normal_user_headers)
    assert resp.status_code in [401, 403]
