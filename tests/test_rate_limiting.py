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


def test_morning_scanning_50_items_load_scenario(rate_limited_client):
    """Simulate a morning scanning session of 50 items with OPTIONS preflights and status polls.

    Under the legacy miscalibrated rate limiter (50 per hour default, OPTIONS counted against quota),
    scanning 50 items instantly triggered HTTP 429 lockouts after ~25 items.
    Under the recalibrated limiter (1000 per hour default, OPTIONS exempt via request_filter):
    - 50 items * 2 requests (CORS OPTIONS preflight + GET) = 100 requests.
    - 10 periodic background status/profile polls = 10 requests.
    - Total: 110 requests in a burst.
    - Result: Zero HTTP 429s, OPTIONS consume 0 tokens, and >900 hourly quota remains.
    """
    for i in range(50):
        # 1. Mobile WebView / Browser sends CORS OPTIONS preflight before each item operation
        resp_opt = rate_limited_client.open("/api/health", method="OPTIONS")
        assert resp_opt.status_code in (200, 204), f"Preflight {i+1} failed with {resp_opt.status_code}"
        opt_headers = {k.lower(): v for k, v in resp_opt.headers.items()}
        assert "x-ratelimit-remaining" not in opt_headers, "OPTIONS preflight must not consume quota"

        # 2. Main item scan / lookup request
        resp_item = rate_limited_client.get("/api/health")
        assert resp_item.status_code == 200, f"Item request {i+1} failed with {resp_item.status_code}"

    # 3. Simulate periodic background status/profile checks during scanning
    for j in range(10):
        resp_poll = rate_limited_client.get("/api/health")
        assert resp_poll.status_code == 200, f"Poll {j+1} failed with {resp_poll.status_code}"

    # Assert exact quota accounting on final response
    final_headers = {k.lower(): v for k, v in resp_poll.headers.items()}
    assert final_headers.get("x-ratelimit-limit") == "1000"
    # Exactly 50 item requests + 10 poll requests = 60 consumed out of 1000
    assert final_headers.get("x-ratelimit-remaining") == "940"
