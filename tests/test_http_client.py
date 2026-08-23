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

import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

from app.utils.http_client import SSRFError, _resolve_with_timeout, is_ip_blocked, is_safe_url, safe_get

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

    @patch("app.utils.http_client.requests.Session.get")
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

    @patch("app.utils.http_client.requests.Session.get")
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

    @patch("app.utils.http_client.requests.Session.get")
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

    @patch("app.utils.http_client.requests.Session.get")
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

    @patch("app.utils.http_client.requests.Session.get")
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

    @patch("app.utils.http_client.requests.Session.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_follows_safe_redirects(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """safe_get should follow redirects to safe IPs."""
        # 1st request -> public, 2nd request -> public
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],
            [(2, 1, 6, "", ("142.250.80.46", 0))],
        ]

        mock_redirect = MagicMock()
        mock_redirect.is_redirect = True
        mock_redirect.headers = {"location": "http://other.com/target"}

        mock_final = MagicMock()
        mock_final.is_redirect = False
        mock_final.status_code = 200

        mock_get.side_effect = [mock_redirect, mock_final]

        result = safe_get("http://example.com/start")

        assert result.status_code == 200
        assert mock_get.call_count == 2
        # First call to 93.184.216.34
        assert "93.184.216.34" in mock_get.call_args_list[0][0][0]
        # Second call to 142.250.80.46
        assert "142.250.80.46" in mock_get.call_args_list[1][0][0]

    @patch("app.utils.http_client.requests.Session.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_blocks_redirect_to_restricted_ip(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """safe_get must block redirects that resolve to a restricted IP."""
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],
            [(2, 1, 6, "", ("127.0.0.1", 0))],
        ]

        mock_redirect = MagicMock()
        mock_redirect.is_redirect = True
        mock_redirect.headers = {"location": "http://localhost/admin"}
        mock_get.return_value = mock_redirect

        with pytest.raises(SSRFError, match="restricted IP"):
            safe_get("http://example.com/start")

    @patch("app.utils.http_client.requests.Session.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_too_many_redirects(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """safe_get must abort after max_redirects."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_redirect = MagicMock()
        mock_redirect.is_redirect = True
        mock_redirect.headers = {"location": "http://example.com/loop"}
        mock_get.return_value = mock_redirect

        with pytest.raises(SSRFError, match="Too many redirects"):
            safe_get("http://example.com/start", max_redirects=2)

        # 3 calls total: hop 0, hop 1, hop 2
        assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# _resolve_with_timeout — DNS timeout enforcement (v0716 hardening)
# ---------------------------------------------------------------------------


class TestResolveWithTimeout:
    """Tests for the ``_resolve_with_timeout`` DNS timeout guard.

    Defense documented for auditors: ``socket.getaddrinfo()`` has no native
    timeout, so a stalling DNS resolver could pin worker threads and starve
    the pool (DNS-based thread starvation).  ``_resolve_with_timeout`` runs
    the lookup in a single-worker ``ThreadPoolExecutor`` and enforces a hard
    5-second ceiling via ``Future.result(timeout=...)`` (http_client.py:57-68).
    """

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_fast_resolution_returns_results(self, mock_getaddrinfo: MagicMock) -> None:
        """A hostname resolving within the timeout must return the getaddrinfo results."""
        expected = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_getaddrinfo.return_value = expected

        assert _resolve_with_timeout("example.com", timeout=5.0) == expected

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_slow_resolution_raises_ssrf_error(self, mock_getaddrinfo: MagicMock) -> None:
        """A stalled lookup must raise SSRFError with a "DNS resolution timed out" message.

        ``Future.result`` is mocked to raise ``concurrent.futures.TimeoutError``
        immediately, so the test never actually sleeps through the 5-second window.
        The mocked getaddrinfo returns instantly so the abandoned worker thread
        completes harmlessly.
        """
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        with patch("concurrent.futures.Future.result", side_effect=concurrent.futures.TimeoutError("DNS timed out")):
            with pytest.raises(SSRFError, match="DNS resolution timed out"):
                _resolve_with_timeout("hanging-dns.example.com", timeout=5.0)


# ---------------------------------------------------------------------------
# safe_get redirect loop — str() coercion (v0716 hardening)
# ---------------------------------------------------------------------------


class _LocationHeader:
    """Non-str object carrying a redirect target; ``__str__`` returns the URL."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value


class TestSafeGetRedirectStrCoercion:
    """Tests for the ``str()`` coercion defense in the ``safe_get`` redirect loop.

    Defense documented for auditors: ``urljoin()`` raises ``TypeError`` when
    given non-str arguments, turning a crafted redirect response into a
    denial of service.  http_client.py:261 coerces both operands —
    ``urljoin(str(current_url), str(next_url))`` — so any object with a
    ``__str__`` (or a bytes value) is handled without crashing.
    """

    @patch("app.utils.http_client.requests.Session.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_redirect_location_object_coerced(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """A non-str location header object must be coerced via ``str()`` and followed correctly."""
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],
            [(2, 1, 6, "", ("142.250.80.46", 0))],
        ]

        mock_redirect = MagicMock()
        mock_redirect.is_redirect = True
        mock_redirect.headers = {"location": _LocationHeader("http://other.com/target")}

        mock_final = MagicMock()
        mock_final.is_redirect = False
        mock_final.status_code = 200

        mock_get.side_effect = [mock_redirect, mock_final]

        result = safe_get("http://example.com/start")

        assert result is mock_final
        assert mock_get.call_count == 2
        # The coerced redirect target was followed to its own resolved IP.
        assert "142.250.80.46" in mock_get.call_args_list[1][0][0]

    @patch("app.utils.http_client.requests.Session.get")
    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_redirect_location_bytes_does_not_raise_typeerror(self, mock_getaddrinfo: MagicMock, mock_get: MagicMock) -> None:
        """A bytes location header must not raise ``TypeError`` from ``urljoin`` (TypeError DoS defense).

        ``str(b"...")`` yields a harmless relative reference that re-joins onto
        the current host; the request completes instead of crashing the worker.
        """
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

        mock_redirect = MagicMock()
        mock_redirect.is_redirect = True
        mock_redirect.headers = {"location": b"http://other.com/target"}

        mock_final = MagicMock()
        mock_final.is_redirect = False
        mock_final.status_code = 200

        mock_get.side_effect = [mock_redirect, mock_final]

        result = safe_get("http://example.com/start")

        assert result is mock_final
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# ThreadPoolExecutor lifecycle — shutdown(wait=False) (v0716 hardening)
# ---------------------------------------------------------------------------


class TestExecutorShutdownLifecycle:
    """Tests for the ``executor.shutdown(wait=False)`` lifecycle defense.

    Defense documented for auditors: ``_resolve_with_timeout`` abandons the
    worker thread when DNS stalls.  Calling ``shutdown(wait=False)`` in the
    ``finally`` block (http_client.py:67-68) releases the executor without
    blocking on the hung thread, preventing starvation under repeated
    timeouts.  The spy below wraps the real ``ThreadPoolExecutor.shutdown``
    and records the ``wait`` argument it receives.
    """

    @staticmethod
    def _spy_shutdown():
        """Return a (spy, recorded_wait_args) pair wrapping the real ThreadPoolExecutor.shutdown."""
        real_shutdown = concurrent.futures.ThreadPoolExecutor.shutdown
        recorded_waits: list[bool] = []

        def spy_shutdown(self, wait=True, **kwargs):
            recorded_waits.append(wait)
            return real_shutdown(self, wait=wait, **kwargs)

        return spy_shutdown, recorded_waits

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_shutdown_wait_false_after_successful_resolution(self, mock_getaddrinfo: MagicMock) -> None:
        """After a successful lookup the executor must be shut down with ``wait=False``."""
        expected = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_getaddrinfo.return_value = expected
        spy_shutdown, recorded_waits = self._spy_shutdown()

        with patch.object(concurrent.futures.ThreadPoolExecutor, "shutdown", spy_shutdown):
            result = _resolve_with_timeout("example.com", timeout=5.0)

        assert result == expected
        assert recorded_waits == [False]

    @patch("app.utils.http_client.socket.getaddrinfo")
    def test_shutdown_wait_false_after_timeout(self, mock_getaddrinfo: MagicMock) -> None:
        """On timeout the ``finally`` block must shut the executor down with ``wait=False``
        *before* the SSRFError propagates to the caller."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        spy_shutdown, recorded_waits = self._spy_shutdown()

        with patch.object(concurrent.futures.ThreadPoolExecutor, "shutdown", spy_shutdown):
            with patch("concurrent.futures.Future.result", side_effect=concurrent.futures.TimeoutError("DNS timed out")):
                with pytest.raises(SSRFError, match="DNS resolution timed out"):
                    _resolve_with_timeout("hanging-dns.example.com", timeout=5.0)

        assert recorded_waits == [False]
