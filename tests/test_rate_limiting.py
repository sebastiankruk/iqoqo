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

"""Tests for rate limiting configuration, headers, and OPTIONS exemptions."""

import pytest

from app import create_app
from app.core.limiter import limiter


@pytest.fixture
def rate_limited_client():
    """Client with rate limiting and headers enabled."""
    app = create_app(
        config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
            "RATELIMIT_ENABLED": True,
            "RATELIMIT_STORAGE_URI": "memory://",
            "RATELIMIT_HEADERS_ENABLED": True,
        }
    )
    with app.app_context():
        yield app.test_client()


def test_limiter_storage_uri_precedence(app):
    """Ensure limiter._storage_uri is None so app.config['RATELIMIT_STORAGE_URI'] governs storage."""
    assert limiter._storage_uri is None
    assert app.config.get("RATELIMIT_HEADERS_ENABLED") is True


def test_default_rate_limits_calibration():
    """Verify default_limits are calibrated to 1000 per hour and 10000 per day."""
    default_limits_str = [str(limit) for limit in limiter.limit_manager.default_limits]
    assert any("1000 per 1 hour" in s for s in default_limits_str)
    assert any("10000 per 1 day" in s for s in default_limits_str)


def test_options_preflight_exempt_from_rate_limiting(rate_limited_client):
    """OPTIONS preflight requests must be exempt from rate limits."""
    for _ in range(10):
        resp = rate_limited_client.open("/api/health", method="OPTIONS")
        assert resp.status_code in (200, 204)
        # OPTIONS request should not emit rate limit consumption headers
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        assert "x-ratelimit-remaining" not in headers_lower


def test_rate_limit_headers_emitted(rate_limited_client):
    """Ensure GET requests emit standard X-RateLimit headers."""
    resp = rate_limited_client.get("/api/health")
    assert resp.status_code == 200
    headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    assert "x-ratelimit-limit" in headers_lower
    assert "x-ratelimit-remaining" in headers_lower
    assert "x-ratelimit-reset" in headers_lower
    assert headers_lower["x-ratelimit-limit"] == "1000"
