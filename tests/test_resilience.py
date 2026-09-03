"""Tests for application startup resilience and Redis fallback behavior."""

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

from unittest.mock import MagicMock, patch

import redis.exceptions

from app import create_app
from app.config import Config


class TestConfig(Config):
    """Test configuration using in-memory SQLite and isolated settings."""

    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    TESTING = True
    WTF_CSRF_ENABLED = False


def test_redis_connection_failure_falls_back_to_memory():
    """Verify Flask gracefully falls back to memory:// and SimpleCache when Redis ping fails."""
    with patch("redis.Redis.from_url") as mock_from_url:
        mock_client = MagicMock()
        mock_client.ping.side_effect = redis.exceptions.ConnectionError("Connection refused")
        mock_from_url.return_value = mock_client

        app = create_app(
            config_class=TestConfig,
            config_override={
                "REDIS_URL": "redis://unreachable-redis:6379/0",
                "RATELIMIT_ENABLED": True,
            },
        )

        assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"
        assert app.config["CACHE_TYPE"] == "SimpleCache"

        client = app.test_client()
        response = client.get("/api/health")
        assert response.status_code == 200


def test_redis_timeout_falls_back_to_memory():
    """Verify Flask falls back to in-memory caching and limiter on Redis timeout."""
    with patch("redis.Redis.from_url") as mock_from_url:
        mock_client = MagicMock()
        mock_client.ping.side_effect = redis.exceptions.TimeoutError("Connection timed out")
        mock_from_url.return_value = mock_client

        app = create_app(
            config_class=TestConfig,
            config_override={
                "REDIS_URL": "redis://slow-redis:6379/0",
                "RATELIMIT_ENABLED": True,
            },
        )

        assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"
        assert app.config["CACHE_TYPE"] == "SimpleCache"


def test_redis_success_configures_redis_cache():
    """Verify Redis caching and limiter storage are configured when Redis ping succeeds."""
    test_redis_url = "redis://mocked-redis:6379/0"
    with patch("redis.Redis.from_url") as mock_from_url:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_from_url.return_value = mock_client

        app = create_app(
            config_class=TestConfig,
            config_override={
                "REDIS_URL": test_redis_url,
            },
        )

        assert app.config["RATELIMIT_STORAGE_URI"] == test_redis_url
        assert app.config["CACHE_TYPE"] == "RedisCache"
        assert app.config["CACHE_REDIS_URL"] == test_redis_url


def test_redis_missing_configures_memory_defaults():
    """Verify in-memory defaults are used when REDIS_URL is not set."""
    app = create_app(
        config_class=TestConfig,
        config_override={
            "REDIS_URL": None,
        },
    )

    assert app.config["RATELIMIT_STORAGE_URI"] == "memory://"
    assert app.config["CACHE_TYPE"] == "SimpleCache"
