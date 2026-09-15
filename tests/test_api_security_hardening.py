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
"""Security tests for API rate limiting and profile avatar validation."""

from unittest.mock import patch

from app.core.limiter import limiter


def test_avatar_url_validation_blocks_unsafe_schemes(client, normal_user_headers):
    """Ensure javascript: and non-HTTP(S) schemes are blocked with 400 Bad Request."""
    res = client.put(
        "/api/profile/",
        json={"avatar_url": "javascript:alert(document.cookie)"},
        headers=normal_user_headers,
    )
    assert res.status_code == 400
    assert "Invalid or unsafe avatar URL" in res.get_json()["error"]


def test_avatar_url_validation_blocks_ssrf_vectors(client, normal_user_headers):
    """Ensure loopback and metadata internal IPs are blocked with 400 Bad Request."""
    ssrf_payloads = [
        "http://127.0.0.1/admin",
        "http://localhost:5000/api/admin",
        "http://169.254.169.254/latest/meta-data/",
    ]
    for url in ssrf_payloads:
        res = client.put(
            "/api/profile/",
            json={"avatar_url": url},
            headers=normal_user_headers,
        )
        assert res.status_code == 400
        assert "Invalid or unsafe avatar URL" in res.get_json()["error"]


def test_avatar_url_validation_accepts_safe_url(client, normal_user_headers):
    """Ensure valid, safe external HTTPS URLs are accepted."""
    with patch("app.api.profile.is_safe_url", return_value=True):
        res = client.put(
            "/api/profile/",
            json={"avatar_url": "https://example.com/valid_avatar.jpg"},
            headers=normal_user_headers,
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["avatar_url"] == "https://example.com/valid_avatar.jpg"


def test_rate_limit_profile_search(app, normal_user_headers):
    """Verify rate limit triggers 429 on profile search endpoint."""
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        hit_429 = False
        for _ in range(35):
            res = test_client.get("/api/profile/search?q=test", headers=normal_user_headers)
            if res.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Expected 429 response on profile search when exceeding rate limit"
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False


def test_rate_limit_rss_feed(app):
    """Verify rate limit triggers 429 on RSS feed endpoint."""
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        hit_429 = False
        for _ in range(65):
            res = test_client.get("/api/public/feed.xml")
            if res.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Expected 429 response on RSS feed when exceeding rate limit"
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False


def test_rate_limit_sharing_creation(app, normal_user_headers):
    """Verify rate limit triggers 429 on collection sharing creation endpoint."""
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    limiter.enabled = True
    limiter._enabled = True
    limiter.init_app(app)
    limiter.reset()

    test_client = app.test_client()

    try:
        hit_429 = False
        for _ in range(35):
            res = test_client.post(
                "/api/sharing",
                json={"name": "Test Share"},
                headers=normal_user_headers,
            )
            if res.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Expected 429 response on sharing creation when exceeding rate limit"
    finally:
        limiter.reset()
        limiter.enabled = False
        limiter._enabled = False
        app.config["RATELIMIT_ENABLED"] = False
