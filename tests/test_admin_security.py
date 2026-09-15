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
"""QA Security tests for Admin API boundary conditions."""

import pytest

from app.config import Config
from app.db.models import Role, db


def test_admin_role_cannot_be_modified(client, admin_headers, app):
    """QA: Ensure the admin role's permissions cannot be modified to prevent system lockout."""
    with app.app_context():
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin")
            db.session.add(admin_role)
            db.session.commit()
        role_id = admin_role.id

    res = client.put(f"/api/v1/admin/roles/{role_id}/permissions", json={"permission_ids": []}, headers=admin_headers)

    assert res.status_code == 400
    assert "Cannot modify permissions of the admin role" in res.json["error"]


def test_get_users_pagination_is_clamped(client, admin_headers):
    """QA: Ensure pagination limit cannot exceed 100 to prevent DoS via unbounded queries."""
    res = client.get("/api/v1/admin/users?limit=999999", headers=admin_headers)

    assert res.status_code == 200
    # Our security fix ensures limit is clamped to 100
    assert res.json["meta"]["limit"] <= 100


# --- Phase 7: SECRET_KEY minimum length validation ---


def test_secret_key_minimum_length_enforced():
    """OWASP A02: SECRET_KEY must be at least 32 bytes in production."""
    with pytest.raises(RuntimeError, match="SECRET_KEY must be at least 32 bytes"):
        Config.validate_secret_key("short-key")


def test_secret_key_valid_length_accepted():
    """Valid SECRET_KEY (>=32 bytes) passes validation."""
    long_key = "a" * 32
    # Should not raise
    Config.validate_secret_key(long_key)


def test_secret_key_insecure_value_rejected():
    """Ensure copy-pasted .env.example or placeholder values are rejected."""
    insecure_values = [
        "changeme_generate_strong_key_for_production",
        "your_super_secret_jwt_key",
        "your_super_secret_auth_key",
        "some_changeme_key",
        "placeholder_key_here",
    ]
    for val in insecure_values:
        with pytest.raises(RuntimeError, match="must not be a default or placeholder value"):
            Config.validate_secret_key(val)


# --- Reveal Settings Security & Rate Limiting ---


def test_reveal_setting_requires_post(client, admin_headers):
    """GET /settings/reveal must return 405 Method Not Allowed."""
    res = client.get("/api/v1/admin/settings/reveal?key=GOOGLE_BOOKS_API_KEY", headers=admin_headers)
    assert res.status_code == 405


def test_reveal_setting_logs_audit(client, app, admin_headers):
    """POST /settings/reveal returns secret and records EntityAuditLog."""
    from app.db.core import EntityAuditLog
    from app.db.models import InstanceSettings

    with app.app_context():
        # Clean up any preexisting setting and add test setting
        InstanceSettings.query.filter_by(key="GOOGLE_BOOKS_API_KEY").delete()
        setting = InstanceSettings(key="GOOGLE_BOOKS_API_KEY", value="super-secret-key-12345")
        db.session.add(setting)
        db.session.commit()

    res = client.post("/api/v1/admin/settings/reveal", json={"key": "GOOGLE_BOOKS_API_KEY"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["value"] == "super-secret-key-12345"

    with app.app_context():
        log = EntityAuditLog.query.filter_by(entity_type="instance_setting", change_type="reveal_secret").first()
        assert log is not None
        assert log.diff.get("key") == "GOOGLE_BOOKS_API_KEY"


def test_reveal_setting_rate_limited(app, admin_headers):
    """POST /settings/reveal enforces 5 per minute rate limiting."""
    from app.core.limiter import limiter

    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        # First 5 calls succeed
        for _ in range(5):
            res = test_client.post("/api/v1/admin/settings/reveal", json={"key": "GOOGLE_BOOKS_API_KEY"}, headers=admin_headers)
            assert res.status_code in (200, 400)

        # 6th call hits rate limit
        res = test_client.post("/api/v1/admin/settings/reveal", json={"key": "GOOGLE_BOOKS_API_KEY"}, headers=admin_headers)
        assert res.status_code == 429
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False
