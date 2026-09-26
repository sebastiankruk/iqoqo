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

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.core.cache import cache
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

    with app.app_context():
        import jwt

        payload = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        assert cache.get(f"token:revoked:{payload['jti']}") == "revoked"

    # 4. Verify JTI is in blocklist
    with app.app_context():
        blocklisted = TokenBlocklist.query.all()
        assert len(blocklisted) > 0

    # 5. Verify token NO LONGER works
    prof_resp_revoked = client.get("/api/profile/", headers=headers)
    assert prof_resp_revoked.status_code == 401
    assert b"Token revoked" in prof_resp_revoked.data


@pytest.mark.parametrize("password", ["", "short", "1234567"])
def test_register_rejects_passwords_shorter_than_eight_characters(client, password):
    response = client.post("/api/auth/register", json={"email": "short-password@iqoqo.local", "password": password})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Password must be at least 8 characters long"


def test_register_accepts_eight_character_password(client):
    response = client.post("/api/auth/register", json={"email": "eight-char-password@iqoqo.local", "password": "12345678"})

    assert response.status_code == 201


def test_token_revocation_cache_miss_falls_back_and_caches_active_state(app):
    from app.api.decorators import _is_token_revoked

    jti = "cache-miss-active-jti"
    cache_key = f"token:revoked:{jti}"
    with app.app_context():
        cache.delete(cache_key)
        expires_at = int((datetime.now(UTC) + timedelta(minutes=2)).timestamp())

        assert _is_token_revoked(jti, expires_at) is False
        assert cache.get(cache_key) == "active"

        with patch("app.api.decorators.db.session.execute", side_effect=AssertionError("cache hit should avoid PostgreSQL")):
            assert _is_token_revoked(jti, expires_at) is False


def test_token_revocation_cache_hit_rejects_without_postgresql(app):
    from app.api.decorators import _is_token_revoked

    jti = "cache-hit-revoked-jti"
    with app.app_context():
        cache.set(f"token:revoked:{jti}", "revoked", timeout=120)
        with patch("app.api.decorators.db.session.execute", side_effect=AssertionError("cache hit should avoid PostgreSQL")):
            assert _is_token_revoked(jti, int((datetime.now(UTC) + timedelta(minutes=2)).timestamp())) is True


def test_token_revocation_cache_miss_finds_blocklist_entry_and_caches_revoked(app):
    from app.api.decorators import _is_token_revoked

    jti = "cache-miss-revoked-jti"
    cache_key = f"token:revoked:{jti}"
    expires_at = datetime.now(UTC) + timedelta(minutes=2)
    with app.app_context():
        cache.delete(cache_key)
        db.session.add(TokenBlocklist(jti=jti, expires_at=expires_at))
        db.session.commit()

        assert _is_token_revoked(jti, int(expires_at.timestamp())) is True
        assert cache.get(cache_key) == "revoked"


def test_token_revocation_cache_failure_falls_back_to_postgresql(app, monkeypatch):
    from app.api.decorators import _is_token_revoked

    jti = "cache-unavailable-revoked-jti"
    with app.app_context():
        db.session.add(TokenBlocklist(jti=jti, expires_at=datetime.now(UTC) + timedelta(minutes=2)))
        db.session.commit()

        def unavailable(*_args, **_kwargs):
            raise OSError("cache unavailable")

        monkeypatch.setattr(cache, "get", unavailable)
        assert _is_token_revoked(jti, int((datetime.now(UTC) + timedelta(minutes=2)).timestamp())) is True


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

    @patch("app.strategies.default.fetch_isbn_metadata", return_value=None)
    @patch("app.utils.isbn._make_session")
    def test_normal_query_accepted(self, mock_session, mock_fetch_isbn, client, admin_headers):
        """A normal-length query should not be rejected for length."""
        resp = client.get("/api/lookup/978-0-123456-47-2", headers=admin_headers)
        # Assuming the system handles it, it might return 200 or 404 (not found).
        # We just want to ensure it doesn't return 400 Bad Request.
        assert resp.status_code in (200, 404)


def test_login_rate_limiting(app):
    """POST /api/auth/login rejects requests beyond 5 per minute."""
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        for _ in range(5):
            res = test_client.post("/api/auth/login", json={"email": "nobody@iqoqo.local", "password": "wrong"})
            assert res.status_code == 401

        res = test_client.post("/api/auth/login", json={"email": "nobody@iqoqo.local", "password": "wrong"})
        assert res.status_code == 429
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False


def test_register_rate_limiting(app):
    """POST /api/auth/register rejects requests beyond 5 per minute."""
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        for i in range(5):
            res = test_client.post(
                "/api/auth/register",
                json={"email": f"ratelimited{i}@iqoqo.local", "password": "password123", "display_name": f"User {i}"},
            )
            assert res.status_code == 201

        res = test_client.post(
            "/api/auth/register",
            json={"email": "ratelimited5@iqoqo.local", "password": "password123", "display_name": "User 5"},
        )
        assert res.status_code == 429
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False
