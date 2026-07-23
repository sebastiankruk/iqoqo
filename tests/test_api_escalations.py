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

"""Tests for custodian escalation requests API."""

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import EscalationRequest, Expression, Item, Manifestation, Permission, Role, User, Work


@pytest.fixture
def escalations_setup(app):
    """Seed database with users, roles, permissions, and FRBR hierarchy."""
    with app.app_context():
        # Setup member role
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

        # Setup custodian role
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

        # Create member user
        u_member = User(email="member1@iqoqo.local", display_name="Member One", public_username="member1")
        u_member.roles.append(member_role)
        db.session.add(u_member)

        # Create custodian user
        u_custodian = User(email="custodian1@iqoqo.local", display_name="Custodian One", public_username="custodian1")
        u_custodian.roles.append(custodian_role)
        db.session.add(u_custodian)

        # Create regular user without permissions
        u_plain = User(email="plain1@iqoqo.local", display_name="Plain One", public_username="plain1")
        db.session.add(u_plain)

        db.session.flush()

        # Create FRBR hierarchy
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

        member_token = generate_internal_jwt(u_member)
        custodian_token = generate_internal_jwt(u_custodian)
        plain_token = generate_internal_jwt(u_plain)

        return {
            "member_id": str(u_member.id),
            "custodian_id": str(u_custodian.id),
            "member_headers": {"Authorization": f"Bearer {member_token}"},
            "custodian_headers": {"Authorization": f"Bearer {custodian_token}"},
            "plain_headers": {"Authorization": f"Bearer {plain_token}"},
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
            "item_id": item.id,
        }


def test_create_escalation_success(client, escalations_setup):
    """Test successful escalation submission with HTML sanitization."""
    headers = escalations_setup["member_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={
            "field_name": "title",
            "current_value": "Wrong Title",
            "suggested_value": "<script>alert('xss')</script>Correct Title",
            "note": "Please fix title <b>now</b>",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    json_data = resp.get_json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert data["manifestation_id"] == manif_id
    assert data["field_name"] == "title"
    assert data["suggested_value"] == "alert('xss')Correct Title"
    assert data["note"] == "Please fix title now"
    assert data["status"] == "pending"


def test_create_escalation_unauthenticated(client, escalations_setup):
    """Test escalation creation without auth header returns 401."""
    manif_id = escalations_setup["manifestation_id"]
    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title", "suggested_value": "New Title"},
    )
    assert resp.status_code == 401


def test_create_escalation_nonexistent_target(client, escalations_setup):
    """Test escalation targeting non-existent entity returns 404."""
    headers = escalations_setup["member_headers"]
    resp = client.post(
        "/api/escalations/manifestation/999999",
        json={"field_name": "title", "suggested_value": "New Title"},
        headers=headers,
    )
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"].lower()


def test_create_escalation_missing_fields(client, escalations_setup):
    """Test escalation submission without required fields returns 400."""
    headers = escalations_setup["member_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"suggested_value": "New Title"},
        headers=headers,
    )
    assert resp.status_code == 400

    resp2 = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title"},
        headers=headers,
    )
    assert resp2.status_code == 400


def test_create_escalation_oversized_text(client, escalations_setup):
    """Test escalation with text > 2048 chars returns 400."""
    headers = escalations_setup["member_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title", "suggested_value": "A" * 2049},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "at most 2048" in resp.get_json()["error"]


def test_list_my_escalations(client, escalations_setup):
    """Test listing user's own escalation requests."""
    headers = escalations_setup["member_headers"]
    manif_id = escalations_setup["manifestation_id"]

    client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "isbn", "suggested_value": "9789999999999"},
        headers=headers,
    )

    resp = client.get("/api/escalations/mine", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert len(data) >= 1
    assert data[0]["field_name"] == "isbn"


def test_list_escalation_queue_and_permissions(client, escalations_setup):
    """Test queue listing requires escalate:resolve permission."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    # Member creates escalation
    client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "format", "suggested_value": "hardcover"},
        headers=member_headers,
    )

    # Member cannot view custodian queue (403)
    resp_member = client.get("/api/escalations/queue", headers=member_headers)
    assert resp_member.status_code == 403

    # Custodian can view queue
    resp_custodian = client.get("/api/escalations/queue", headers=custodian_headers)
    assert resp_custodian.status_code == 200
    queue = resp_custodian.get_json()["data"]
    assert len(queue) >= 1
    assert queue[0]["status"] == "pending"


def test_resolve_escalation_request(client, escalations_setup):
    """Test resolving escalation request by custodian."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    # Create request
    resp_create = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title", "suggested_value": "Revised Title"},
        headers=member_headers,
    )
    esc_id = resp_create.get_json()["data"]["id"]

    # Non-custodian resolution attempt fails with 403
    resp_bad = client.patch(
        f"/api/escalations/{esc_id}",
        json={"status": "accepted"},
        headers=member_headers,
    )
    assert resp_bad.status_code == 403

    # Custodian accepts request
    resp_resolve = client.patch(
        f"/api/escalations/{esc_id}",
        json={"status": "accepted", "resolution_note": "Applied in editor"},
        headers=custodian_headers,
    )
    assert resp_resolve.status_code == 200
    resolved = resp_resolve.get_json()["data"]
    assert resolved["status"] == "accepted"
    assert resolved["resolution_note"] == "Applied in editor"
    assert resolved["resolved_by"] == escalations_setup["custodian_id"]


def test_cascade_delete_escalation(app, client, escalations_setup):
    """Test that deleting target Manifestation cascade-deletes the escalation request."""
    member_headers = escalations_setup["member_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp_create = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title", "suggested_value": "Title To Delete"},
        headers=member_headers,
    )
    esc_id = resp_create.get_json()["data"]["id"]

    with app.app_context():
        manif = db.session.get(Manifestation, manif_id)
        db.session.delete(manif)
        db.session.commit()

        esc = db.session.get(EscalationRequest, esc_id)
        assert esc is None


def test_submit_to_retrieve_pipeline(client, escalations_setup):
    """End-to-end submit-to-retrieve: member submits escalation, then sees it via /mine and /queue."""
    member_headers = escalations_setup["member_headers"]
    custodian_headers = escalations_setup["custodian_headers"]
    manif_id = escalations_setup["manifestation_id"]

    # Submit escalation
    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={
            "field_name": "title",
            "suggested_value": "Pipeline Test Title",
        },
        headers=member_headers,
    )
    assert resp.status_code == 201
    created = resp.get_json()["data"]
    esc_id = created["id"]

    # Verify visible in /mine
    resp_mine = client.get("/api/escalations/mine", headers=member_headers)
    assert resp_mine.status_code == 200
    mine_data = resp_mine.get_json()["data"]
    mine_ids = [e["id"] for e in mine_data]
    assert esc_id in mine_ids

    # Verify visible in /queue
    resp_queue = client.get("/api/escalations/queue", headers=custodian_headers)
    assert resp_queue.status_code == 200
    queue_data = resp_queue.get_json()["data"]
    queue_ids = [e["id"] for e in queue_data]
    assert esc_id in queue_ids


def test_custodian_can_view_queue(client, escalations_setup):
    """Verify that a custodian (non-admin) can call GET /api/escalations/queue and receive 200."""
    custodian_headers = escalations_setup["custodian_headers"]

    resp = client.get("/api/escalations/queue", headers=custodian_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


def test_plain_user_without_permission_cannot_create_escalation(client, escalations_setup):
    """Verify that a user without escalate:request permission gets 403 when trying to create an escalation."""
    plain_headers = escalations_setup["plain_headers"]
    manif_id = escalations_setup["manifestation_id"]

    resp = client.post(
        f"/api/escalations/manifestation/{manif_id}",
        json={"field_name": "title", "suggested_value": "Should Not Work"},
        headers=plain_headers,
    )
    assert resp.status_code == 403
