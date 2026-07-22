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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Tests for telemetry header and URL sanitization functions."""

from unittest.mock import patch

import pytest

from app.core.telemetry import record_outbound_telemetry, sanitize_headers, sanitize_url


@pytest.mark.parametrize(
    ("header_name", "header_value", "expected_value"),
    [
        ("Authorization", "Bearer secret-token", "***REDACTED***"),
        ("X-API-KEY", "1234567890", "***REDACTED***"),
        ("x-amz-security-token", "amz-token-val", "***REDACTED***"),
        ("Cookie", "sessionid=xyz", "***REDACTED***"),
        ("Set-Cookie", "sessionid=xyz; Secure", "***REDACTED***"),
        ("X-Session-ID", "sess-abc-123", "***REDACTED***"),
        ("User-Agent", "iqoqo-agent/1.0", "iqoqo-agent/1.0"),
        ("Accept", "application/json", "application/json"),
        ("Content-Type", "application/json; charset=utf-8", "application/json; charset=utf-8"),
    ],
)
def test_sanitize_headers(header_name: str, header_value: str, expected_value: str) -> None:
    """Verify sensitive headers are redacted while harmless headers are preserved."""
    headers = {header_name: header_value}
    result = sanitize_headers(headers)
    assert result[header_name] == expected_value


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        ("https://api.example.com?api_key=SECRET&page=1", "https://api.example.com?api_key=%2A%2A%2AREDACTED%2A%2A%2A&page=1"),
        (
            "https://s3.amazonaws.com/bucket?X-Amz-Signature=abc&X-Amz-Credential=def",
            "https://s3.amazonaws.com/bucket?X-Amz-Signature=%2A%2A%2AREDACTED%2A%2A%2A&X-Amz-Credential=%2A%2A%2AREDACTED%2A%2A%2A",
        ),
        ("https://example.com/path", "https://example.com/path"),
        ("", ""),
        (None, None),
    ],
)
def test_sanitize_url(raw_url: str | None, expected_url: str | None) -> None:
    """Verify sensitive query params are redacted in URLs."""
    result = sanitize_url(raw_url)
    assert result == expected_url


def test_sanitize_url_malformed() -> None:
    """Verify malformed URL returns error sentinel on parse failure."""
    with patch("app.core.telemetry.urlparse", side_effect=ValueError("Invalid URL")):
        result = sanitize_url("https://invalid-url-triggering-exception")
        assert result == "***REDACTED_URL_PARSE_ERROR***"


def test_record_outbound_telemetry_integration() -> None:
    """Verify record_outbound_telemetry redacts headers and handles OTel unavailability gracefully."""
    raw_headers = {
        "Authorization": "Bearer token123",
        "User-Agent": "test-agent",
    }
    url = "https://api.example.com?token=secret123"

    sanitized = record_outbound_telemetry("TestService", raw_headers, url=url)
    assert sanitized["Authorization"] == "***REDACTED***"
    assert sanitized["User-Agent"] == "test-agent"
