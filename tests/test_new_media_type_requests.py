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
"""Tests for user escalation requests for new media types and physical formats."""

import json
from unittest.mock import patch

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import EscalationRequest, Permission, Role, User
from app.db.social import Notification


@pytest.fixture
def new_media_type_setup(app):
    """Seed test database with roles, permissions, and users for new_media_type tests."""
    with app.app_context():
        # Setup member role & user
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

        # Setup custodian role & user
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

        u_member = User(email="collector1@iqoqo.local", display_name="Collector One", public_username="collector1")
        u_member.roles.append(member_role)
        db.session.add(u_member)

        u_custodian = User(email="custodian_type@iqoqo.local", display_name="Custodian Type", public_username="custodian_type")
        u_custodian.roles.append(custodian_role)
        db.session.add(u_custodian)

        u_plain = User(email="plain_type@iqoqo.local", display_name="Plain User", public_username="plain_type")
        db.session.add(u_plain)

        db.session.commit()

        member_token = generate_internal_jwt(u_member)
        custodian_token = generate_internal_jwt(u_custodian)
        plain_token = generate_internal_jwt(u_plain)

        return {
            "member_id": u_member.id,
            "custodian_id": u_custodian.id,
            "member_headers": {"Authorization": f"Bearer {member_token}"},
            "custodian_headers": {"Authorization": f"Bearer {custodian_token}"},
            "plain_headers": {"Authorization": f"Bearer {plain_token}"},
        }


def test_create_new_media_type_escalation_success(client, new_media_type_setup):
    """Collector successfully submits a new media type proposal."""
    payload = {
        "request_type": "new_media_type",
        "proposed_category": "video",
        "proposed_format": "LaserDisc",
        "parent_frbr_class": "F1_Work",
        "sample_identifier_or_url": "https://example.com/ld/123",
        "suggested_properties": ["laserdisc_side_count", "disc_size"],
        "rationale": "12-inch optical video disc format requiring dedicated physical cataloging",
    }

    resp = client.post("/api/escalations", json=payload, headers=new_media_type_setup["member_headers"])
    assert resp.status_code == 201
    data = resp.json
    assert data["success"] is True

    esc = data["data"]
    assert esc["request_type"] == "new_media_type"
    assert esc["status"] == "pending"
    assert esc["manifestation_id"] is None
    assert esc["work_id"] is None
    assert esc["expression_id"] is None
    assert esc["item_id"] is None
    assert esc["target_type"] == "new_media_type"

    # Verify target entity projection
    target_entity = esc["target_entity"]
    assert target_entity is not None
    assert target_entity["type"] == "NewMediaType"
    assert target_entity["title"] == "LaserDisc"
    assert target_entity["current_state"] == "video"

    # Verify notification created for custodian
    notifs = Notification.query.filter_by(
        user_id=new_media_type_setup["custodian_id"],
        type="new_media_type_requested",
    ).all()
    assert len(notifs) >= 1
    assert "LaserDisc" in notifs[0].payload_json.get("proposed_format", "")


def test_create_new_media_type_validation_errors(client, new_media_type_setup):
    """Payload validation correctly rejects missing fields and invalid inputs."""
    headers = new_media_type_setup["member_headers"]

    # 1. Missing proposed_format
    resp = client.post(
        "/api/escalations",
        json={"request_type": "new_media_type", "proposed_category": "video", "rationale": "Sample rationale"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "proposed_format" in resp.json["error"]

    # 2. Missing proposed_category
    resp = client.post(
        "/api/escalations",
        json={"request_type": "new_media_type", "proposed_format": "LaserDisc", "rationale": "Sample rationale"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "proposed_category" in resp.json["error"]

    # 3. Missing rationale
    resp = client.post(
        "/api/escalations",
        json={"request_type": "new_media_type", "proposed_category": "video", "proposed_format": "LaserDisc"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "rationale" in resp.json["error"]

    # 4. Invalid parent_frbr_class
    resp = client.post(
        "/api/escalations",
        json={
            "request_type": "new_media_type",
            "proposed_category": "video",
            "proposed_format": "LaserDisc",
            "parent_frbr_class": "InvalidClass",
            "rationale": "Sample rationale",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "parent_frbr_class" in resp.json["error"]

    # 5. Invalid general escalation request_type
    resp = client.post(
        "/api/escalations",
        json={"request_type": "correction", "rationale": "Invalid without target"},
        headers=headers,
    )
    assert resp.status_code == 400

    # 6. Unauthenticated request
    resp = client.post(
        "/api/escalations",
        json={"request_type": "new_media_type", "proposed_category": "video", "proposed_format": "LaserDisc", "rationale": "Test"},
    )
    assert resp.status_code == 401

    # 7. Plain user without escalate:request permission
    resp = client.post(
        "/api/escalations",
        json={"request_type": "new_media_type", "proposed_category": "video", "proposed_format": "LaserDisc", "rationale": "Test"},
        headers=new_media_type_setup["plain_headers"],
    )
    assert resp.status_code == 403


def test_my_escalations_and_queue_for_new_media_type(client, new_media_type_setup):
    """User can view their new media type proposal and custodian can inspect queue."""
    member_headers = new_media_type_setup["member_headers"]
    custodian_headers = new_media_type_setup["custodian_headers"]

    create_resp = client.post(
        "/api/escalations",
        json={
            "request_type": "new_media_type",
            "proposed_category": "music",
            "proposed_format": "MiniDisc",
            "rationale": "Magneto-optical disc data storage format",
        },
        headers=member_headers,
    )
    assert create_resp.status_code == 201
    esc_id = create_resp.json["data"]["id"]

    # Member lists their escalations
    mine_resp = client.get("/api/escalations/mine", headers=member_headers)
    assert mine_resp.status_code == 200
    my_items = [e for e in mine_resp.json["data"] if e["id"] == esc_id]
    assert len(my_items) == 1
    assert my_items[0]["target_entity"]["title"] == "MiniDisc"
    assert my_items[0]["target_entity"]["current_state"] == "music"

    # Custodian lists escalation queue
    queue_resp = client.get("/api/escalations/queue?status=pending", headers=custodian_headers)
    assert queue_resp.status_code == 200
    queue_items = [e for e in queue_resp.json["data"] if e["id"] == esc_id]
    assert len(queue_items) == 1
    assert queue_items[0]["target_entity"]["title"] == "MiniDisc"

    # Custodian fetches single escalation detail
    detail_resp = client.get(f"/api/escalations/{esc_id}", headers=custodian_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json["data"]["target_entity"]["title"] == "MiniDisc"


def test_custodian_resolves_new_media_type(client, new_media_type_setup):
    """Custodian can accept or reject new media type proposal and notify the collector."""
    member_headers = new_media_type_setup["member_headers"]
    custodian_headers = new_media_type_setup["custodian_headers"]

    create_resp = client.post(
        "/api/escalations",
        json={
            "request_type": "new_media_type",
            "proposed_category": "games",
            "proposed_format": "ArcadePCB",
            "rationale": "Printed circuit board for arcade cabinets",
        },
        headers=member_headers,
    )
    assert create_resp.status_code == 201
    esc_id = create_resp.json["data"]["id"]

    # Resolve proposal with acceptance
    resolve_resp = client.patch(
        f"/api/escalations/{esc_id}",
        json={"status": "accepted", "resolution_note": "Approved! Added to roadmap taxonomy update."},
        headers=custodian_headers,
    )
    assert resolve_resp.status_code == 200
    data = resolve_resp.json["data"]
    assert data["status"] == "accepted"
    assert data["resolution_note"] == "Approved! Added to roadmap taxonomy update."

    # Verify notification sent to member
    member_notifs = Notification.query.filter_by(
        user_id=new_media_type_setup["member_id"],
        type="new_media_type_resolved",
    ).all()
    assert len(member_notifs) >= 1
    assert f"#{esc_id} was accepted" in member_notifs[0].payload_json.get("message", "")
