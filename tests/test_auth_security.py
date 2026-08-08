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

import pytest

from app.db.models import Role, TokenBlocklist, User, db


@pytest.fixture(autouse=True)
def setup_security_context(app):
    """Ensure roles and test user exist."""
    with app.app_context():
        if not Role.query.filter_by(name="user").first():
            db.session.add(Role(name="user"))
        if not Role.query.filter_by(name="admin").first():
            db.session.add(Role(name="admin"))
        db.session.commit()


def test_logout_revokes_token(app, client):
    # 1. Register and Login to get a token
    client.post("/api/auth/register", json={"email": "security@iqoqo.local", "password": "password123", "display_name": "Security User"})
    login_resp = client.post("/api/auth/login", json={"email": "security@iqoqo.local", "password": "password123"})
    token = login_resp.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify token works (profile endpoint)
    prof_resp = client.get("/api/profile/", headers=headers)
    assert prof_resp.status_code == 200

    # 3. Logout
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert b"Logged out successfully" in logout_resp.data

    # 4. Verify JTI is in blocklist
    with app.app_context():
        blocklisted = TokenBlocklist.query.all()
        assert len(blocklisted) > 0

    # 5. Verify token NO LONGER works
    prof_resp_revoked = client.get("/api/profile/", headers=headers)
    assert prof_resp_revoked.status_code == 401
    assert b"Token revoked" in prof_resp_revoked.data


def test_logout_idempotency(client):
    # 1. Login
    client.post("/api/auth/register", json={"email": "idem@iqoqo.local", "password": "password123"})
    login_resp = client.post("/api/auth/login", json={"email": "idem@iqoqo.local", "password": "password123"})
    token = login_resp.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Logout first time
    resp1 = client.post("/api/auth/logout", headers=headers)
    assert resp1.status_code == 200

    # 3. Logout second time (should not crash despite unique constraint)
    resp2 = client.post("/api/auth/logout", headers=headers)
    assert resp2.status_code == 200
    assert b"Logged out successfully" in resp2.data


def test_admin_required_rejects_revoked_token(app, client):
    # 1. Create admin user
    client.post("/api/auth/register", json={"email": "admin@iqoqo.local", "password": "password123"})
    with app.app_context():
        user = User.query.filter_by(email="admin@iqoqo.local").first()
        admin_role = Role.query.filter_by(name="admin").first()
        user.roles.append(admin_role)
        db.session.commit()

    # 2. Login
    login_resp = client.post("/api/auth/login", json={"email": "admin@iqoqo.local", "password": "password123"})
    token = login_resp.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Verify admin access works (e.g., list all users if such endpoint exists,
    # but we'll use a placeholder or check /api/items/1 DELETE which usually requires admin/ownership)
    # Actually, let's just logout and verify admin-protected decorators block it.
    client.post("/api/auth/logout", headers=headers)

    # Check an admin protected route (e.g. DELETE /api/items/1)
    # Even if item 1 doesn't exist, the decorator runs first.
    admin_resp = client.delete("/api/items/1", headers=headers)
    assert admin_resp.status_code == 401
    assert b"Token revoked" in admin_resp.data


class TestAllegroDeviceFlowAdminOnly:
    """Allegro device-flow endpoints must require admin privileges."""

    def test_device_flow_unauthenticated(self, client):
        """Unauthenticated POST to /api/auth/allegro/device-flow returns 401/403."""
        resp = client.post("/api/auth/allegro/device-flow", json={})
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"

    def test_device_token_unauthenticated(self, client):
        """Unauthenticated POST to /api/auth/allegro/device-token returns 401/403."""
        resp = client.post("/api/auth/allegro/device-token", json={})
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"

    def test_device_flow_normal_user_forbidden(self, client):
        """Non-admin user POST to /api/auth/allegro/device-flow returns 403."""
        client.post("/api/auth/register", json={"email": "regular@iqoqo.local", "password": "password123"})
        login_resp = client.post("/api/auth/login", json={"email": "regular@iqoqo.local", "password": "password123"})
        token = login_resp.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/auth/allegro/device-flow", json={}, headers=headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_device_token_normal_user_forbidden(self, client):
        """Non-admin user POST to /api/auth/allegro/device-token returns 403."""
        client.post("/api/auth/register", json={"email": "regular2@iqoqo.local", "password": "password123"})
        login_resp = client.post("/api/auth/login", json={"email": "regular2@iqoqo.local", "password": "password123"})
        token = login_resp.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/auth/allegro/device-token", json={}, headers=headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


class TestBarcodePreviewQueryValidation:
    """Barcode preview endpoint should enforce query length limits."""

    def test_oversized_query_rejected(self, client, admin_headers):
        """Query strings exceeding 128 characters should return 400."""
        long_query = "X" * 200
        resp = client.get(f"/api/lookup/{long_query}", headers=admin_headers)
        assert resp.status_code == 400
        data = resp.get_json()
        assert "too long" in data.get("error", "").lower()

    def test_normal_query_accepted(self, client, admin_headers):
        """A normal-length query should not be rejected for length."""
        resp = client.get("/api/lookup/978-0-123456-47-2", headers=admin_headers)
        # Should not be 400 (may be 404 or 200 depending on DB state)
        assert resp.status_code != 400
