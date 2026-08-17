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
"""Tests for user feedback tickets and administration RBAC endpoints."""

import uuid

import pytest

from app.core.permissions import PermissionName
from app.db.models import FeedbackItem, Permission, Role, User, db


@pytest.fixture
def feedback_setup(app):
    """Seed test users, roles, and permissions for feedback tests."""
    with app.app_context():
        # Ensure tickets permissions exist
        p_admin = db.session.execute(db.select(Permission).filter_by(name="tickets:admin")).scalar_one_or_none()
        if not p_admin:
            p_admin = Permission(name="tickets:admin", description="Administer tickets")
            db.session.add(p_admin)

        p_creator = db.session.execute(db.select(Permission).filter_by(name="tickets:creator")).scalar_one_or_none()
        if not p_creator:
            p_creator = Permission(name="tickets:creator", description="Create tickets")
            db.session.add(p_creator)

        r_admin = db.session.execute(db.select(Role).filter_by(name="admin")).scalar_one_or_none()
        if not r_admin:
            r_admin = Role(name="admin")
            db.session.add(r_admin)
        if p_admin not in r_admin.permissions:
            r_admin.permissions.append(p_admin)

        r_user = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
        if not r_user:
            r_user = Role(name="user")
            db.session.add(r_user)
        if p_creator not in r_user.permissions:
            r_user.permissions.append(p_creator)

        # Users
        u_admin = User(email="admin_fb@example.com", display_name="Admin User", is_active=True)
        u_admin.set_password("AdminPass123!")
        u_admin.roles.append(r_admin)
        db.session.add(u_admin)

        u_creator1 = User(email="user1_fb@example.com", display_name="User One", is_active=True)
        u_creator1.set_password("UserPass123!")
        u_creator1.roles.append(r_user)
        db.session.add(u_creator1)

        u_creator2 = User(email="user2_fb@example.com", display_name="User Two", is_active=True)
        u_creator2.set_password("UserPass123!")
        u_creator2.roles.append(r_user)
        db.session.add(u_creator2)

        db.session.commit()

        return {
            "admin_id": u_admin.id,
            "user1_id": u_creator1.id,
            "user2_id": u_creator2.id,
        }


def _auth_headers(app, user_id: uuid.UUID) -> dict[str, str]:
    import jwt

    token = jwt.encode({"sub": str(user_id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_submit_and_list_feedback_rbac(client, feedback_setup, app):
    """Test creating tickets, scoping list results by user role, and pagination."""
    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    u2_headers = _auth_headers(app, feedback_setup["user2_id"])
    admin_headers = _auth_headers(app, feedback_setup["admin_id"])

    # User 1 submits a bug
    resp = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "Found a visual bug on sidebar"},
        headers=u1_headers,
    )
    assert resp.status_code == 201
    u1_ticket_id = resp.json["data"]["id"]
    assert resp.json["data"]["status"] == "new"

    # User 2 submits a feature request
    resp = client.post(
        "/api/feedback",
        data={"type": "feature_request", "description": "Add dark mode toggle in footer"},
        headers=u2_headers,
    )
    assert resp.status_code == 201
    u2_ticket_id = resp.json["data"]["id"]

    # User 1 lists tickets -> sees only User 1's ticket
    resp = client.get("/api/feedback", headers=u1_headers)
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    assert data[0]["id"] == u1_ticket_id

    # Admin lists tickets -> sees all tickets with requester info
    resp = client.get("/api/feedback", headers=admin_headers)
    assert resp.status_code == 200
    all_tickets = resp.json["data"]
    assert len(all_tickets) >= 2
    assert any(t["id"] == u1_ticket_id and t["user_email"] == "user1_fb@example.com" for t in all_tickets)
    assert any(t["id"] == u2_ticket_id and t["user_email"] == "user2_fb@example.com" for t in all_tickets)


def test_ticket_status_lifecycle_and_comments(client, feedback_setup, app):
    """Test admin changing status, comments thread, and creator closing ticket."""
    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    admin_headers = _auth_headers(app, feedback_setup["admin_id"])

    # User 1 submits a ticket
    resp = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "Cannot upload heavy PNG"},
        headers=u1_headers,
    )
    ticket_id = resp.json["data"]["id"]

    # Creator tries to set status to in_progress -> forbidden
    resp = client.patch(f"/api/feedback/{ticket_id}", json={"status": "in_progress"}, headers=u1_headers)
    assert resp.status_code == 403

    # Admin updates status to in_progress and leaves a comment
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"status": "in_progress", "comment": "Investigating upload limit"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json["data"]["status"] == "in_progress"
    assert len(resp.json["data"]["comments"]) == 1
    assert resp.json["data"]["comments"][0]["comment"] == "Investigating upload limit"

    # Creator adds comment
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"comment": "Thanks, it happens for files > 5MB"},
        headers=u1_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json["data"]["comments"]) == 2

    # Creator closes own ticket
    resp = client.patch(f"/api/feedback/{ticket_id}", json={"status": "closed"}, headers=u1_headers)
    assert resp.status_code == 200
    assert resp.json["data"]["status"] == "closed"


def test_feedback_closed_ticket_comment_rejected(client, feedback_setup, app):
    """Commenting on a closed ticket is rejected with HTTP 400."""
    u1_headers = _auth_headers(app, feedback_setup["user1_id"])

    # Create and close ticket
    submit = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "Issue with search filter"},
        headers=u1_headers,
    )
    ticket_id = submit.json["data"]["id"]
    client.patch(f"/api/feedback/{ticket_id}", json={"status": "closed"}, headers=u1_headers)

    # Attempt to comment on closed ticket
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"comment": "Adding comment to closed ticket"},
        headers=u1_headers,
    )
    assert resp.status_code == 400
    assert resp.json["error"] == "Cannot add comments to a closed ticket"


def test_feedback_pagination_clamping(client, feedback_setup, app):
    """Negative page and excessive per_page parameters are clamped safely."""
    admin_headers = _auth_headers(app, feedback_setup["admin_id"])

    resp = client.get("/api/feedback?page=-1&per_page=500", headers=admin_headers)
    assert resp.status_code == 200
    pagination = resp.json["pagination"]
    assert pagination["page"] == 1
    assert pagination["per_page"] == 100


def test_feedback_upload_count_cap(client, feedback_setup, app):
    """Submitting more than 5 screenshots is rejected with HTTP 400."""
    from io import BytesIO

    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    screenshots = [(BytesIO(png_bytes), f"shot_{i}.png") for i in range(6)]
    resp = client.post(
        "/api/feedback",
        data={
            "type": "bug",
            "description": "Exceeded attachment limit test",
            "screenshots": screenshots,
        },
        headers=u1_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.json["error"] == "Maximum 5 screenshots allowed per ticket"


def test_feedback_get_rate_limiting(client, feedback_setup, app):
    """GET /api/feedback rejects requests beyond 60/minute when rate limiting is enabled."""
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    try:
        admin_headers = _auth_headers(app, feedback_setup["admin_id"])
        responses = [client.get("/api/feedback", headers=admin_headers) for _ in range(61)]
        assert [r.status_code for r in responses[:60]] == [200] * 60
        assert responses[60].status_code == 429
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False
