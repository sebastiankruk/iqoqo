"""Tests for the SSRF-safe HTTP client wrapper (app.utils.http_client).

Verifies that the client correctly blocks requests to restricted IP ranges
(localhost, RFC 1918, link-local / cloud metadata) and handles DNS rebinding
edge cases safely.
"""

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

import pytest

from app.utils.http_client import SSRFError, is_ip_blocked, is_safe_url, safe_get

# ---------------------------------------------------------------------------
# is_ip_blocked
# ---------------------------------------------------------------------------


class TestIsIpBlocked:
    """Tests for the is_ip_blocked helper function."""

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",
            "127.0.0.2",
            "10.0.0.1",
            "10.255.255.255",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.0.1",
            "192.168.1.100",
            "169.254.169.254",  # AWS metadata endpoint
            "169.254.0.1",
            "::1",  # IPv6 loopback
        ],
    )
    def test_blocks_restricted_ips(self, ip: str) -> None:
        """Blocked IPs include loopback, RFC 1918, link-local, and IPv6 equivalents."""
        assert is_ip_blocked(ip) is True

    @pytest.mark.parametrize(
        "ip",
        [
            "8.8.8.8",
            "1.1.1.1",
            "93.184.216.34",
            "142.250.80.46",
        ],
    )
    def test_allows_public_ips(self, ip: str) -> None:
        """Public, routable IPs should be allowed."""
        assert is_ip_blocked(ip) is False

    def test_blocks_invalid_ip_string(self) -> None:
        """Unparseable strings are treated as blocked for safety."""
        assert is_ip_blocked("not-an-ip") is True


# ---------------------------------------------------------------------------
# is_safe_url
# ---------------------------------------------------------------------------


class TestIsSafeUrl:
    """Tests for the is_safe_url validation function."""

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_localhost(self, mock_getaddrinfo: MagicMock) -> None:
        """Requests to localhost must be blocked."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ]
        assert is_safe_url("http://localhost/secret") is False

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_metadata_endpoint(self, mock_getaddrinfo: MagicMock) -> None:
        """Cloud metadata endpoint (169.254.169.254) must be blocked."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("169.254.169.254", 0)),
        ]
        assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_rfc1918_via_dns(self, mock_getaddrinfo: MagicMock) -> None:
        """Domain resolving to RFC 1918 address must be blocked (DNS rebinding protection)."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("10.0.0.1", 0)),
        ]
        assert is_safe_url("http://evil-rebinding.example.com/data") is False

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_allows_public_url(self, mock_getaddrinfo: MagicMock) -> None:
        """Public URLs should pass validation."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        assert is_safe_url("https://example.com/image.jpg") is True

    def test_blocks_ftp_scheme(self) -> None:
        """Non-HTTP/HTTPS schemes must be blocked."""
        assert is_safe_url("ftp://example.com/file") is False

    def test_blocks_missing_hostname(self) -> None:
        """URLs without a hostname must be blocked."""
        assert is_safe_url("http:///path") is False

    def test_blocks_empty_url(self) -> None:
        """Empty URLs must be blocked."""
        assert is_safe_url("") is False


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------


class TestSafeGet:
    """Tests for the safe_get SSRF-safe HTTP GET wrapper."""

    @patch("app.utils.http_client.requests.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_successful_public_request(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """Requests to public IPs should succeed and pass through the Host header."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = safe_get("http://example.com/image.jpg", headers={"User-Agent": "test"})

        assert result.status_code == 200
        # Verify the request was rewritten to use the resolved IP
        call_args = mock_get.call_args
        assert "93.184.216.34" in call_args[0][0]
        # Verify Host header was set
        assert call_args[1]["headers"]["Host"] == "example.com"

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_localhost_request(self, mock_getaddrinfo: MagicMock) -> None:
        """safe_get must raise SSRFError for localhost."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ]
        with pytest.raises(SSRFError, match="restricted IP"):
            safe_get("http://localhost/admin")

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_metadata_request(self, mock_getaddrinfo: MagicMock) -> None:
        """safe_get must raise SSRFError for cloud metadata endpoints."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("169.254.169.254", 0)),
        ]
        with pytest.raises(SSRFError, match="restricted IP"):
            safe_get("http://169.254.169.254/latest/meta-data/")

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_dns_rebinding_to_private(self, mock_getaddrinfo: MagicMock) -> None:
        """DNS rebinding to a private IP must be caught and blocked."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.1", 0)),
        ]
        with pytest.raises(SSRFError, match="restricted IP"):
            safe_get("http://attacker.com/payload")

    def test_blocks_unsupported_scheme(self) -> None:
        """Non-HTTP/HTTPS schemes must raise SSRFError."""
        with pytest.raises(SSRFError, match="Unsupported scheme"):
            safe_get("ftp://files.example.com/data")

    def test_blocks_missing_hostname(self) -> None:
        """URLs without a hostname must raise SSRFError."""
        with pytest.raises(SSRFError, match="Missing hostname"):
            safe_get("http:///path/to/resource")

    @patch("app.utils.http_client.socket.getaddrinfo", side_effect=OSError("DNS failure"))
    def test_dns_failure_raises_ssrf_error(self, mock_getaddrinfo: MagicMock) -> None:
        """DNS resolution failures must raise SSRFError, not leak through."""
        with pytest.raises(SSRFError, match="DNS resolution failed"):
            safe_get("http://nonexistent.example.com/image.jpg")

    @patch("app.utils.http_client.requests.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_preserves_original_host_header(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """The original hostname must be sent as the Host header to prevent TLS/vhost issues."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("142.250.80.46", 0)),
        ]
        mock_get.return_value = MagicMock(status_code=200)

        safe_get("http://www.google.com/path")

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Host"] == "www.google.com"

    @patch("app.utils.http_client.requests.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_does_not_override_existing_host_header(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """If a Host header is already set, safe_get should not override it."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        mock_get.return_value = MagicMock(status_code=200)

        safe_get("http://example.com/path", headers={"Host": "custom-host.com"})

        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Host"] == "custom-host.com"

    @patch("app.utils.http_client.requests.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_port_preserved_in_rewritten_url(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """Port numbers must be preserved when rewriting the URL to use the resolved IP."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        mock_get.return_value = MagicMock(status_code=200)

        safe_get("http://example.com:8080/path")

        call_args = mock_get.call_args
        assert "93.184.216.34:8080" in call_args[0][0]

    @patch("app.utils.http_client.requests.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_https_not_rewritten(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """HTTPS URLs must not be rewritten to IP addresses to avoid SSL certificate mismatch."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        mock_get.return_value = MagicMock(status_code=200)

        safe_get("https://example.com/path")

        call_args = mock_get.call_args
        # URL should be unchanged
        assert call_args[0][0] == "https://example.com/path"
        # No extra Host header should be injected since we didn't rewrite
        assert "Host" not in call_args[1].get("headers", {})
