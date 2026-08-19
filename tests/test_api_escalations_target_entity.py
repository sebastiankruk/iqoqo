"""Tests for escalation target entity enrichment and approval validation."""

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

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import EscalationRequest, Expression, Item, Manifestation, Permission, Role, User, Work


@pytest.fixture
def escalations_setup(app):
    """Seed database with users, roles, permissions, and FRBR hierarchy."""
    with app.app_context():
        member_role = Role.query.filter_by(name="member").first()
        if not member_role:
            member_role = Role(name="member")
            db.session.add(member_role)

        req_perm = Permission.query.filter_by(name="escalate:request").first()
        if not req_perm:
            req_perm = Permission(name="escalate:request")
            db.session.add(req_perm)
        if req_perm not in member_role.permissions:
            member_role.permissions.append(req_perm)

        custodian_role = Role.query.filter_by(name="custodian").first()
        if not custodian_role:
            custodian_role = Role(name="custodian")
            db.session.add(custodian_role)

        resolve_perm = Permission.query.filter_by(name="escalate:resolve").first()
        if not resolve_perm:
            resolve_perm = Permission(name="escalate:resolve")
            db.session.add(resolve_perm)
        if resolve_perm not in custodian_role.permissions:
            custodian_role.permissions.append(resolve_perm)

        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.session.add(admin_role)

        del_manif_perm = Permission.query.filter_by(name="delete:manifestation").first()
        if not del_manif_perm:
            del_manif_perm = Permission(name="delete:manifestation")
            db.session.add(del_manif_perm)
        if del_manif_perm not in admin_role.permissions:
            admin_role.permissions.append(del_manif_perm)
        if resolve_perm not in admin_role.permissions:
            admin_role.permissions.append(resolve_perm)

        u_member = User(email="member1@iqoqo.local", display_name="Member One", public_username="member1")
        u_member.roles.append(member_role)
        db.session.add(u_member)

        u_custodian = User(email="custodian1@iqoqo.local", display_name="Custodian One", public_username="custodian1")
        u_custodian.roles.append(custodian_role)
        db.session.add(u_custodian)

        u_admin = User(email="admin1@iqoqo.local", display_name="Admin One", public_username="admin1")
        u_admin.roles.append(admin_role)
        db.session.add(u_admin)

        u_plain = User(email="plain1@iqoqo.local", display_name="Plain One", public_username="plain1")
        db.session.add(u_plain)

        db.session.flush()

        work = Work(title="Escalation Test Work", meta={"authors": ["Author E"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9781234567890", meta={"format": "book"})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=u_member.id, status="available")
        db.session.add(item)
        db.session.commit()

        return {
            "member_id": str(u_member.id),
            "custodian_id": str(u_custodian.id),
            "admin_id": str(u_admin.id),
            "member_headers": {"Authorization": f"Bearer {generate_internal_jwt(u_member)}"},
            "custodian_headers": {"Authorization": f"Bearer {generate_internal_jwt(u_custodian)}"},
            "admin_headers": {"Authorization": f"Bearer {generate_internal_jwt(u_admin)}"},
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
            "item_id": item.id,
        }


def test_escalation_detail_returns_target_entity(client, escalations_setup):
    """GET /api/escalations/<id> includes target_entity with required fields."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "type", "suggested_value": "hardcover"},
        headers=member_headers,
    )
    esc_id = resp.get_json()["data"]["id"]

    detail = client.get(f"/api/escalations/{esc_id}", headers=custodian_headers)
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["success"] is True

    target = body["data"]["target_entity"]
    assert target is not None
    assert target["id"] == manif_id
    assert target["type"] == "Manifestation"
    assert "title" in target
    assert "current_state" in target


def test_escalation_queue_returns_target_entity(client, escalations_setup):
    """GET /api/escalations/queue enriches each entry with target_entity."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "type", "suggested_value": "hardcover"},
        headers=member_headers,
    )

    queue = client.get("/api/escalations/queue", headers=custodian_headers)
    assert queue.status_code == 200
    data = queue.get_json()["data"]
    assert len(data) >= 1
    for entry in data:
        assert "target_entity" in entry
        if entry["manifestation_id"] == manif_id:
            assert entry["target_entity"]["type"] == "Manifestation"
            assert entry["target_entity"]["id"] == manif_id


def test_approval_with_mismatched_target_id_is_rejected(client, escalations_setup):
    """Accepting a change_type request with a mismatched target_id returns 400."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"request_type": "change_type", "field_name": "type", "suggested_value": "hardcover"},
        headers=member_headers,
    )
    esc_id = resp.get_json()["data"]["id"]

    resolve = client.patch(
        f"/api/escalations/{esc_id}",
        json={"status": "accepted", "target_id": 999999},
        headers=custodian_headers,
    )
    assert resolve.status_code == 400
    assert "does not match" in resolve.get_json()["error"].lower()


def test_approval_with_matching_target_id_is_accepted(client, escalations_setup):
    """Accepting a change_type request with the correct target_id succeeds."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"request_type": "change_type", "field_name": "type", "suggested_value": "book"},
        headers=member_headers,
    )
    esc_id = resp.get_json()["data"]["id"]

    resolve = client.patch(
        f"/api/escalations/{esc_id}",
        json={"status": "accepted", "target_id": manif_id},
        headers=custodian_headers,
    )
    assert resolve.status_code == 200
    assert resolve.get_json()["data"]["status"] == "accepted"
