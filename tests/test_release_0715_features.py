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
"""Comprehensive test suite for v0.7.15 backend features and edge cases.

Covers:
1. In-App Feedback API validation, character limits, invalid filter params, and RBAC boundaries.
2. Dashboard and Insights query scoping (?scope=personal vs ?scope=global) across multi-user inventories.
3. Ownership facet filtering edge cases and unauthenticated defaults.
"""

import uuid
from io import BytesIO

import jwt
import pytest

from app.db.models import (
    Expression,
    FeedbackItem,
    Item,
    Manifestation,
    Permission,
    Role,
    User,
    Work,
    db,
)


@pytest.fixture
def multi_user_setup(app):
    """Seed multiple users with distinct items and tickets to test scoping and RBAC."""
    with app.app_context():
        # Setup roles and permissions
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

        # Create Admin
        u_admin = User(email="admin_0715@iqoqo.local", display_name="Admin 0715", is_active=True)
        u_admin.set_password("AdminPass123!")
        u_admin.roles.append(r_admin)
        db.session.add(u_admin)

        # Create User A
        u_a = User(email="user_a@iqoqo.local", display_name="User A", is_active=True)
        u_a.set_password("UserPass123!")
        u_a.roles.append(r_user)
        db.session.add(u_a)

        # Create User B
        u_b = User(email="user_b@iqoqo.local", display_name="User B", is_active=True)
        u_b.set_password("UserPass123!")
        u_b.roles.append(r_user)
        db.session.add(u_b)

        db.session.flush()

        # Seed Catalog
        work1 = Work(title="Sci-Fi Chronicle", meta={"genres": ["Sci-Fi"]})
        work2 = Work(title="Historical Epic", meta={"genres": ["History"]})
        db.session.add_all([work1, work2])
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="text", language="en")
        expr2 = Expression(work_id=work2.id, content_type="text", language="en")
        db.session.add_all([expr1, expr2])
        db.session.flush()

        m1 = Manifestation(expression_id=expr1.id, isbn13="9780111111111", meta={"format": "Paperback"})
        m2 = Manifestation(expression_id=expr2.id, isbn13="9780222222222", meta={"format": "Hardcover"})
        db.session.add_all([m1, m2])
        db.session.flush()

        # User A owns 2 items of Manifestation 1
        item_a1 = Item(manifestation_id=m1.id, owner_id=u_a.id, status="available")
        item_a2 = Item(manifestation_id=m1.id, owner_id=u_a.id, status="reading")
        # User B owns 1 item of Manifestation 2
        item_b1 = Item(manifestation_id=m2.id, owner_id=u_b.id, status="available")
        db.session.add_all([item_a1, item_a2, item_b1])

        # Seed feedback item for User A
        fb_a = FeedbackItem(
            user_id=u_a.id,
            feedback_type="bug",
            description="Button alignment issue on mobile",
            status="new",
        )
        db.session.add(fb_a)
        db.session.commit()

        token_a = jwt.encode({"sub": str(u_a.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        token_b = jwt.encode({"sub": str(u_b.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        token_admin = jwt.encode({"sub": str(u_admin.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")

        return {
            "admin_id": u_admin.id,
            "user_a_id": u_a.id,
            "user_b_id": u_b.id,
            "headers_a": {"Authorization": f"Bearer {token_a}"},
            "headers_b": {"Authorization": f"Bearer {token_b}"},
            "headers_admin": {"Authorization": f"Bearer {token_admin}"},
            "m1_id": m1.id,
            "m2_id": m2.id,
            "fb_a_id": fb_a.id,
        }


@pytest.fixture
def feedback_rate_limiter(app):
    """Enable the production limiter for the endpoint-specific rate-limit test."""
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False
    limiter._enabled = False
    app.config["RATELIMIT_ENABLED"] = False


# ===========================================================================
# 1. In-App Feedback API Validations & Edge Cases
# ===========================================================================


def test_feedback_submit_invalid_type_rejected(client, multi_user_setup):
    """Submitting feedback with an invalid type returns HTTP 400."""
    resp = client.post(
        "/api/feedback",
        data={"type": "unsupported_type", "description": "Valid description here"},
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False
    assert "type must be feature_request or bug" in resp.json["error"]


def test_feedback_submit_empty_description_rejected(client, multi_user_setup):
    """Submitting feedback without a description returns HTTP 400."""
    resp = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "   "},
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False
    assert "description is required" in resp.json["error"]


def test_feedback_submit_oversized_description_rejected(client, multi_user_setup):
    """Submitting feedback with description > 20000 chars returns HTTP 400."""
    oversized = "a" * 20_001
    resp = client.post(
        "/api/feedback",
        data={"type": "bug", "description": oversized},
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False


def test_feedback_list_invalid_status_filter_rejected(client, multi_user_setup):
    """Filtering tickets with an invalid status query parameter returns HTTP 400."""
    resp = client.get(
        "/api/feedback?status=nonexistent_status",
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False
    assert "Invalid feedback status" in resp.json["error"]


def test_feedback_list_invalid_type_filter_rejected(client, multi_user_setup):
    """Filtering tickets with an invalid type query parameter returns HTTP 400."""
    resp = client.get(
        "/api/feedback?type=unknown_type",
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False
    assert "Invalid feedback type" in resp.json["error"]


def test_feedback_non_owner_view_forbidden(client, multi_user_setup):
    """A standard user cannot view another user's private feedback ticket."""
    resp = client.get(
        f"/api/feedback/{multi_user_setup['fb_a_id']}",
        headers=multi_user_setup["headers_b"],
    )
    assert resp.status_code == 403
    assert resp.json["success"] is False


def test_feedback_non_owner_patch_forbidden(client, multi_user_setup):
    """A standard user cannot modify another user's feedback ticket."""
    resp = client.patch(
        f"/api/feedback/{multi_user_setup['fb_a_id']}",
        json={"comment": "Attempting unauthorized comment"},
        headers=multi_user_setup["headers_b"],
    )
    assert resp.status_code == 403
    assert resp.json["success"] is False


def test_feedback_get_nonexistent_returns_404(client, multi_user_setup):
    """Requesting a non-existent feedback ticket returns HTTP 404."""
    resp = client.get(
        "/api/feedback/999999",
        headers=multi_user_setup["headers_a"],
    )
    assert resp.status_code == 404
    assert resp.json["success"] is False


def test_feedback_creator_can_submit_and_close_own_ticket(client, multi_user_setup):
    """The creator permission permits submission and closing, but not arbitrary transitions."""
    submit = client.post(
        "/api/feedback",
        data={"type": "bug", "description": "A reproducible scanner problem"},
        headers=multi_user_setup["headers_a"],
    )
    assert submit.status_code == 201
    ticket_id = submit.json["data"]["id"]

    rejected = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"status": "in_progress"},
        headers=multi_user_setup["headers_a"],
    )
    assert rejected.status_code == 403

    closed = client.patch(
        f"/api/feedback/{ticket_id}",
        json={"status": "closed"},
        headers=multi_user_setup["headers_a"],
    )
    assert closed.status_code == 200
    assert closed.json["data"]["status"] == "closed"


def test_feedback_admin_can_list_all_and_resolve_ticket(client, multi_user_setup):
    """tickets:admin can see another user's ticket and update its lifecycle."""
    listed = client.get("/api/feedback", headers=multi_user_setup["headers_admin"])
    assert listed.status_code == 200
    assert multi_user_setup["fb_a_id"] in [ticket["id"] for ticket in listed.json["data"]]

    resolved = client.patch(
        f"/api/feedback/{multi_user_setup['fb_a_id']}",
        json={"status": "in_validation", "comment": "Reproduced and fixed."},
        headers=multi_user_setup["headers_admin"],
    )
    assert resolved.status_code == 200
    assert resolved.json["data"]["status"] == "in_validation"
    assert resolved.json["data"]["comments"][-1]["comment"] == "Reproduced and fixed."


def test_feedback_rejects_invalid_screenshot(client, multi_user_setup):
    """Only supported image uploads are accepted as feedback attachments."""
    resp = client.post(
        "/api/feedback",
        data={
            "type": "bug",
            "description": "Attachment validation",
            "screenshots": (BytesIO(b"not an image"), "evidence.txt"),
        },
        headers=multi_user_setup["headers_a"],
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.json["success"] is False


def test_feedback_submission_is_rate_limited(client, multi_user_setup, feedback_rate_limiter):
    """The submission endpoint rejects the sixth request within its one-hour window."""
    responses = [
        client.post(
            "/api/feedback",
            data={"type": "bug", "description": f"Rate limit test {index}"},
            headers=multi_user_setup["headers_a"],
        )
        for index in range(6)
    ]
    assert [response.status_code for response in responses[:5]] == [201] * 5
    assert responses[5].status_code == 429


# ===========================================================================
# 2. Multi-User Scoped Query Isolation (?scope=personal vs ?scope=global)
# ===========================================================================


def test_stats_personal_scope_multiuser_isolation(client, multi_user_setup):
    """User A sees 2 items in personal scope, User B sees 1 item, global scope sees all 3+ items."""
    # User A personal scope
    resp_a = client.get("/api/stats?scope=personal", headers=multi_user_setup["headers_a"])
    assert resp_a.status_code == 200
    data_a = resp_a.json["data"]
    assert data_a["total_items"] == 2

    # User B personal scope
    resp_b = client.get("/api/stats?scope=personal", headers=multi_user_setup["headers_b"])
    assert resp_b.status_code == 200
    data_b = resp_b.json["data"]
    assert data_b["total_items"] == 1

    # User A global scope
    resp_global = client.get("/api/stats?scope=global", headers=multi_user_setup["headers_a"])
    assert resp_global.status_code == 200
    data_global = resp_global.json["data"]
    assert data_global["total_items"] >= 3


def test_profile_insights_scope_parameter_handling(client, multi_user_setup):
    """Insights endpoints isolate personal item aggregates from global aggregates."""
    for ep in ["velocity", "distribution"]:
        resp_p = client.get(f"/api/profile/insights/{ep}?scope=personal", headers=multi_user_setup["headers_a"])
        assert resp_p.status_code == 200
        assert resp_p.json["success"] is True

        resp_g = client.get(f"/api/profile/insights/{ep}?scope=global", headers=multi_user_setup["headers_a"])
        assert resp_g.status_code == 200
        assert resp_g.json["success"] is True

        if ep == "velocity":
            assert sum(row["count"] for row in resp_p.json["data"]) == 2
            assert sum(row["count"] for row in resp_g.json["data"]) >= 3
        else:
            assert sum(row["count"] for row in resp_p.json["data"]["by_type"]) == 2
            assert sum(row["count"] for row in resp_g.json["data"]["by_type"]) >= 3


# ===========================================================================
# 3. Ownership Facet Navigation Edge Cases
# ===========================================================================


def test_manifestations_ownership_filtering_user_a(client, multi_user_setup):
    """User A owns Manifestation 1 but not Manifestation 2."""
    # Owned by User A
    resp_owned = client.get("/api/manifestations?ownership=owned", headers=multi_user_setup["headers_a"])
    assert resp_owned.status_code == 200
    ids_owned = [item["id"] for item in resp_owned.json["data"]]
    assert multi_user_setup["m1_id"] in ids_owned
    assert multi_user_setup["m2_id"] not in ids_owned

    # Not owned by User A
    resp_not_owned = client.get("/api/manifestations?ownership=not_owned", headers=multi_user_setup["headers_a"])
    assert resp_not_owned.status_code == 200
    ids_not_owned = [item["id"] for item in resp_not_owned.json["data"]]
    assert multi_user_setup["m1_id"] not in ids_not_owned
    assert multi_user_setup["m2_id"] in ids_not_owned
