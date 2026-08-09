"""SSRF-safe HTTP client wrapper for external resource fetching.

Prevents Server-Side Request Forgery by resolving hostnames to IP addresses
*before* making requests and blocking connections to private, loopback,
link-local, and cloud metadata IP ranges.  Protects against DNS rebinding
by connecting directly to the resolved IP while preserving the original
``Host`` header.
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

import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool

logger = logging.getLogger(__name__)

# Blocked IPv4 networks — RFC 1918 private, loopback, link-local, and
# cloud metadata endpoints.
_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.IPv4Network("127.0.0.0/8"),  # Loopback
    ipaddress.IPv4Network("10.0.0.0/8"),  # RFC 1918
    ipaddress.IPv4Network("172.16.0.0/12"),  # RFC 1918
    ipaddress.IPv4Network("192.168.0.0/16"),  # RFC 1918
    ipaddress.IPv4Network("169.254.0.0/16"),  # Link-local (includes AWS metadata 169.254.169.254)
    ipaddress.IPv6Network("::1/128"),  # IPv6 loopback
    ipaddress.IPv6Network("fc00::/7"),  # IPv6 unique local (RFC 4193)
    ipaddress.IPv6Network("fe80::/10"),  # IPv6 link-local
]


class SSRFError(Exception):
    """Raised when a request targets a restricted IP range."""


def is_ip_blocked(ip_str: str) -> bool:
    """Check whether an IP address falls within any restricted network range.

    Args:
        ip_str: String representation of an IP address.

    Returns:
        ``True`` if the address is in a restricted range, ``False`` otherwise.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        # Unparseable addresses are treated as blocked for safety.
        return True

    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
        return True

    for network in _BLOCKED_NETWORKS:
        if ip_obj in network:
            return True

    return False


def is_safe_url(url: str) -> bool:
    """Validate that a URL targets a publicly routable host.

    Resolves the hostname via DNS and verifies that *none* of the resulting IP
    addresses fall within restricted ranges.  Returns ``False`` for unsafe URLs
    (private IPs, loopback, link-local, non-HTTP schemes, missing hostname).

    Args:
        url: The URL to validate.

    Returns:
        ``True`` if safe, ``False`` otherwise.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(5)
            ip_info = socket.getaddrinfo(hostname, None)
        finally:
            socket.setdefaulttimeout(old_timeout)

        for result in ip_info:
            ip_str = str(result[4][0])
            if is_ip_blocked(ip_str):
                logger.warning(
                    "SSRF Attempt Blocked: Hostname %s resolved to restricted IP %s.",
                    hostname,
                    ip_str,
                )
                return False
        return True
    except (TimeoutError, OSError, ValueError, socket.gaierror) as exc:
        logger.error("URL validation failed for %s: %s", url, exc)
        return False


class PinningHTTPSConnection(HTTPSConnection):
    """HTTPS connection that connects to a specific pinned IP but keeps original SNI."""

    def __init__(self, *args, **kwargs):
        self.pinned_ip = kwargs.pop("pinned_ip", None)
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        original_host = self.host
        if self.pinned_ip:
            self.host = self.pinned_ip
        try:
            return super()._new_conn()  # pylint: disable=no-member  # urllib3 HTTPSConnection internal method
        finally:
            self.host = original_host


class SSRFProtectionAdapter(HTTPAdapter):
    """Adapter that forces HTTPS connections to use a pinned IP address."""

    def __init__(self, pinned_ip: str, *args, **kwargs):
        self.pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        conn = super().get_connection(url, proxies)
        if isinstance(conn, HTTPSConnectionPool):
            conn.ConnectionCls = PinningHTTPSConnection
            conn.conn_kw["pinned_ip"] = self.pinned_ip
        return conn


def safe_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    timeout: int | float | tuple[int | float, int | float] = 10,
    stream: bool = False,
    max_redirects: int = 5,
) -> requests.Response:
    """Perform an SSRF-safe HTTP GET request.

    Resolves the hostname to an IP address, validates it against restricted
    ranges, and makes the request directly to the resolved IP with the original
    ``Host`` header (for HTTP) or via socket-level IP pinning (for HTTPS)
    to prevent DNS rebinding. Follows redirects safely up to max_redirects by
    re-resolving and re-validating the target on each hop.

    Args:
        url: Target URL.
        headers: Optional HTTP headers.
        params: Optional query parameters.
        timeout: Request timeout (seconds or (connect, read) tuple).
        stream: Whether to stream the response body.
        max_redirects: Maximum number of redirects to follow safely.

    Returns:
        :class:`requests.Response` object.

    Raises:
        SSRFError: If the target resolves to a restricted IP address or too many redirects.
        requests.RequestException: On network errors.
    """
    current_url = url
    session = requests.Session()

    for hop in range(max_redirects + 1):
        parsed = urlparse(current_url)
        if parsed.scheme not in ("http", "https"):
            raise SSRFError(f"Unsupported scheme: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFError("Missing hostname in URL")

        # Resolve hostname to IP *before* connecting with explicit timeout.
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(5)
            addr_results = socket.getaddrinfo(hostname, None)
        except TimeoutError as exc:
            raise SSRFError(f"DNS resolution timed out for {hostname}") from exc
        except (socket.gaierror, OSError) as exc:
            raise SSRFError(f"DNS resolution failed for {hostname}") from exc
        finally:
            socket.setdefaulttimeout(old_timeout)

        if not addr_results:
            raise SSRFError(f"DNS resolution returned no results for {hostname}")

        # Validate ALL resolved IPs — block if any are restricted.
        resolved_ip: str | None = None
        for result in addr_results:
            ip_str = str(result[4][0])
            if is_ip_blocked(ip_str):
                raise SSRFError(f"Blocked: {hostname} resolved to restricted IP {ip_str}")
            if resolved_ip is None:
                resolved_ip = ip_str

        assert resolved_ip is not None  # guaranteed by non-empty addr_results  # noqa: S101

        merged_headers = dict(headers or {})
        request_params = params if hop == 0 else None

        if parsed.scheme == "https":
            rewritten_url = current_url
            adapter = SSRFProtectionAdapter(pinned_ip=resolved_ip)
            session.mount("https://", adapter)
        else:
            port = parsed.port
            if port:
                netloc = f"{resolved_ip}:{port}"
            else:
                netloc = resolved_ip

            rewritten_url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            merged_headers.setdefault("Host", hostname)

        response = session.get(
            rewritten_url,
            headers=merged_headers,
            params=request_params,
            timeout=timeout,
            stream=stream,
            verify=True,
            allow_redirects=False,
        )

        if getattr(response, "is_redirect", False) is True:
            if hop >= max_redirects:
                raise SSRFError("Too many redirects")
            next_url = response.headers.get("location")
            if not next_url:
                raise SSRFError("Redirect missing location header")
            current_url = urljoin(str(current_url), str(next_url))
        else:
            return response

    raise SSRFError("Too many redirects")
