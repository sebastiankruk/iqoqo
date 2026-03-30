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

import json

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


def test_logout_revokes_token(client):
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
    # In a real JWT, we'd decode it to find JTI, but here we check DB directly
    # assuming the logout logic successfully added it.
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


def test_admin_required_rejects_revoked_token(client):
    # 1. Create admin user
    client.post("/api/auth/register", json={"email": "admin@iqoqo.local", "password": "password123"})
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
