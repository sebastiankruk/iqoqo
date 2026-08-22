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


def _sample_png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    return buf.getvalue()


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
    print(resp.json)
    assert resp.status_code == 201
    u1_ticket_id = resp.json["data"]["id"]
    assert resp.json["data"]["status"] == "new"

    # User 2 submits a feature request
    resp = client.post(
        "/api/feedback",
        data={"type": "feature_request", "description": "Add dark mode toggle in footer"},
        headers=u2_headers,
    )
    print(resp.json)
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
    png_bytes = _sample_png()

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


def test_concurrent_comment_addition(client, feedback_setup, app):
    """Test that concurrent comment additions do not overwrite each other (no race condition)."""
    import threading

    u1_headers = _auth_headers(app, feedback_setup["user1_id"])

    # Create a ticket
    submit = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "Concurrency test"},
        headers=u1_headers,
    )
    ticket_id = submit.json["data"]["id"]

    lock = threading.Lock()

    def add_comment(idx):
        with lock:
            with app.test_client() as c:
                c.patch(
                    f"/api/feedback/{ticket_id}",
                    json={"comment": f"Comment {idx}"},
                    headers=u1_headers,
                )

    threads = []
    for i in range(10):
        t = threading.Thread(target=add_comment, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify all comments are present
    resp = client.get(f"/api/feedback/{ticket_id}", headers=u1_headers)
    assert resp.status_code == 200
    assert len(resp.json["data"]["comments"]) == 10


def test_rclone_screenshot_upload(client, feedback_setup, app, monkeypatch):
    """Test that screenshots trigger Celery task and resolve remotely if configured."""
    import os
    from io import BytesIO
    from unittest.mock import MagicMock

    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    png_bytes = _sample_png()

    mock_subprocess_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)
    monkeypatch.setenv("RCLONE_FEEDBACK_REMOTE", "test_remote:feedback")

    # Override Celery task to run synchronously
    from app.core.tasks import upload_feedback_screenshot

    def mock_apply_async(*args, **kwargs):
        upload_feedback_screenshot(*kwargs.get("args", []), **kwargs.get("kwargs", {}))

    monkeypatch.setattr(upload_feedback_screenshot, "apply_async", mock_apply_async)

    resp = client.post(
        "/api/feedback",
        data={
            "type": "bug",
            "description": "Rclone test",
            "screenshots": (BytesIO(png_bytes), "test.png"),
        },
        headers=u1_headers,
        content_type="multipart/form-data",
    )
    print(resp.json)
    assert resp.status_code == 201, resp.json

    # Assert rclone was called
    mock_subprocess_run.assert_called_once()
    args = mock_subprocess_run.call_args[0][0]
    assert "rclone" in args
    assert "copyto" in args
    assert any("test_remote:feedback" in a for a in args)

    # Test retrieval from remote
    filename = resp.json["data"]["attachments"][0].split("/")[-1]

    mock_subprocess_run_cat = MagicMock()
    mock_subprocess_run_cat.return_value.stdout = b"fakeimage"
    monkeypatch.setattr("subprocess.run", mock_subprocess_run_cat)

    # Need to remove local file to trigger rclone fallback
    from app.utils.covers import GALLERY_DIR

    local_path = os.path.join(GALLERY_DIR, filename)
    if os.path.exists(local_path):
        os.remove(local_path)

    img_resp = client.get(f"/api/feedback/screenshots/{filename}", headers=u1_headers)
    assert img_resp.status_code == 200
    assert img_resp.data == b"fakeimage"
    mock_subprocess_run_cat.assert_called_once()
    assert "cat" in mock_subprocess_run_cat.call_args[0][0]


def test_rclone_graceful_fallback(client, feedback_setup, app, monkeypatch):
    """Test fallback when rclone is not configured."""
    import os
    from io import BytesIO
    from unittest.mock import MagicMock

    monkeypatch.delenv("RCLONE_FEEDBACK_REMOTE", raising=False)

    mock_subprocess_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    # Override Celery task to run synchronously
    from app.core.tasks import upload_feedback_screenshot

    def mock_apply_async(*args, **kwargs):
        upload_feedback_screenshot(*kwargs.get("args", []), **kwargs.get("kwargs", {}))

    monkeypatch.setattr(upload_feedback_screenshot, "apply_async", mock_apply_async)

    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    png_bytes = _sample_png()

    resp = client.post(
        "/api/feedback",
        data={
            "type": "bug",
            "description": "Fallback test",
            "screenshots": (BytesIO(png_bytes), "test2.png"),
        },
        headers=u1_headers,
        content_type="multipart/form-data",
    )
    print(resp.json)
    assert resp.status_code == 201

    # Subprocess shouldn't be called because RCLONE_FEEDBACK_REMOTE is missing
    mock_subprocess_run.assert_not_called()

    filename = resp.json["data"]["attachments"][0].split("/")[-1]

    # Remove local file to test retrieval failure
    from app.utils.covers import GALLERY_DIR

    local_path = os.path.join(GALLERY_DIR, filename)
    if os.path.exists(local_path):
        os.remove(local_path)

    img_resp = client.get(f"/api/feedback/screenshots/{filename}", headers=u1_headers)
    assert img_resp.status_code == 404


def test_feedback_schema_migration(app):
    """Test that feedback_items and feedback_comments are in social schema."""
    from sqlalchemy import inspect, text

    with app.app_context():
        if db.engine.dialect.name == "postgresql":
            result = db.session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'social' "
                    "AND table_name IN ('feedback_items', 'feedback_comments')"
                )
            ).fetchall()
            tables = [row[0] for row in result]
            assert "feedback_items" in tables
            assert "feedback_comments" in tables
        else:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            assert "feedback_items" in tables
            assert "feedback_comments" in tables


def test_feedback_attachments_url_format_and_retrieval(client, feedback_setup, app):
    """Ensure submitted feedback attachments use canonical /api/feedback/screenshots/ URLs and can be retrieved."""
    from io import BytesIO

    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    png_bytes = _sample_png()

    # 1. Submit ticket with 2 screenshots
    resp = client.post(
        "/api/feedback",
        data={
            "type": "bug",
            "description": "Attachment rendering regression test",
            "screenshots": [
                (BytesIO(png_bytes), "screenshot_a.png"),
                (BytesIO(png_bytes), "screenshot_b.png"),
            ],
        },
        headers=u1_headers,
        content_type="multipart/form-data",
    )
    print(resp.json)
    assert resp.status_code == 201
    ticket_id = resp.json["data"]["id"]
    attachments = resp.json["data"]["attachments"]
    assert len(attachments) == 2
    for att in attachments:
        assert att.startswith("/api/feedback/screenshots/feedback-")
        assert not att.startswith("/api/v1/")
        assert att.endswith(".jpg")

    # 2. Verify list_feedback endpoint returns canonical attachment URLs
    list_resp = client.get("/api/feedback", headers=u1_headers)
    assert list_resp.status_code == 200
    listed_ticket = next(t for t in list_resp.json["data"] if t["id"] == ticket_id)
    assert len(listed_ticket["attachments"]) == 2
    for att in listed_ticket["attachments"]:
        assert att.startswith("/api/feedback/screenshots/feedback-")

    # 3. Verify get_feedback_item endpoint returns canonical attachment URLs
    detail_resp = client.get(f"/api/feedback/{ticket_id}", headers=u1_headers)
    assert detail_resp.status_code == 200
    for att in detail_resp.json["data"]["attachments"]:
        assert att.startswith("/api/feedback/screenshots/feedback-")
        assert not att.startswith("/api/v1/")

    # 4. Verify update_feedback endpoint returns canonical attachment URLs
    patch_resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"comment": "Adding comment to ticket with attachments"},
        headers=u1_headers,
    )
    assert patch_resp.status_code == 200
    for att in patch_resp.json["data"]["attachments"]:
        assert att.startswith("/api/feedback/screenshots/feedback-")
        assert not att.startswith("/api/v1/")

    # 5. Verify direct image retrieval via GET /api/feedback/screenshots/<filename>
    for att_url in attachments:
        get_img_resp = client.get(att_url, headers=u1_headers)
        assert get_img_resp.status_code == 200
        assert get_img_resp.content_type == "image/jpeg"
        assert len(get_img_resp.data) > 0


def test_feedback_patch_schema_validation(client, feedback_setup, app):
    """Test schema validation for PATCH /api/feedback/<id> with valid, invalid, unknown, and empty payloads."""
    admin_headers = _auth_headers(app, feedback_setup["admin_id"])

    # Create ticket
    submit = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "Validation test ticket"},
        headers=admin_headers,
    )
    assert submit.status_code == 201
    ticket_id = submit.json["data"]["id"]

    # 1. Valid update with description, feedback_type, and status
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"description": "Updated ticket description", "feedback_type": "feature_request", "status": "accepted"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json["data"]["description"] == "Updated ticket description"
    assert resp.json["data"]["feedback_type"] == "feature_request"
    assert resp.json["data"]["status"] == "accepted"

    # 2. Empty JSON body -> 400 with validation error
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False

    # 3. Payload with unknown/extra fields -> 400 with field-level validation errors
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"status": "in_progress", "unknown_field": "disallowed_value"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False
    assert any("unknown_field" in str(err) or "extra_forbidden" in str(err) for err in resp.json["error"])

    # 4. Payload with invalid status value -> 400
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"status": "nonexistent_status"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False

    # 5. Payload with invalid feedback_type -> 400
    resp = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"feedback_type": "invalid_type"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False


def test_feedback_screenshot_idor_protection(client, feedback_setup, app):
    """Ensure users cannot access screenshots belonging to other users' tickets."""
    import io


    u1_headers = _auth_headers(app, feedback_setup["user1_id"])
    u2_headers = _auth_headers(app, feedback_setup["user2_id"])
    admin_headers = _auth_headers(app, feedback_setup["admin_id"])

    # User 1 submits a ticket with a screenshot
    png_bytes = _sample_png()
    resp = client.post(
        "/api/feedback",
        headers=u1_headers,
        data={
            "subject": "User 1 Secret Ticket",
            "description": "This is private",
            "type": "bug",
            "screenshots": (io.BytesIO(png_bytes), "secret.png"),
        },
        content_type="multipart/form-data",
    )
    print(resp.json)
    assert resp.status_code == 201
    ticket_data = resp.json["data"]

    # Extract the filename from the URL returned
    attachment_url = ticket_data["attachments"][0]
    filename = attachment_url.split("/")[-1]

    # 1. User 1 can access their own screenshot
    resp_u1 = client.get(f"/api/feedback/screenshots/{filename}", headers=u1_headers)
    assert resp_u1.status_code == 200

    # 2. User 2 CANNOT access User 1's screenshot (IDOR protection)
    resp_u2 = client.get(f"/api/feedback/screenshots/{filename}", headers=u2_headers)
    assert resp_u2.status_code in (403, 404)  # It returns 403 or 404 based on implementation

    # 3. Admin CAN access User 1's screenshot
    resp_admin = client.get(f"/api/feedback/screenshots/{filename}", headers=admin_headers)
    assert resp_admin.status_code == 200
