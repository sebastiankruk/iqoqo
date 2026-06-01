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
"""Federation HTTP client with SSRF prevention and HTTP signature support."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.federation_keys import get_actor_private_key
from app.core.http_signatures import sign_request

logger = logging.getLogger(__name__)

# Timeout configuration (seconds)
_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 30

# Maximum response size (10 MB)
_MAX_RESPONSE_SIZE = 10 * 1024 * 1024


class SSRFError(Exception):
    """Raised when a request targets a private/blocked IP address."""


class FederationDeliveryError(Exception):
    """Raised when activity delivery fails after retries."""


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or otherwise dangerous."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # Invalid IP → block

    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        # Block AWS IMDS
        or ip_str == "169.254.169.254"
    )


def _validate_url(url: str) -> None:
    """Validate a URL is safe to fetch (no SSRF).

    Resolves the hostname and checks the IP against blocklists.
    Raises SSRFError if the URL targets a private address.
    """
    parsed = urlparse(url)

    if not parsed.hostname:
        raise SSRFError(f"Invalid URL (no hostname): {url}")

    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Invalid URL scheme: {parsed.scheme}")

    # Resolve hostname to IPs
    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFError(f"DNS resolution failed for {parsed.hostname}: {exc}") from exc

    for addr_info in addr_infos:
        ip = str(addr_info[4][0])
        if _is_private_ip(ip):
            raise SSRFError(f"Blocked request to private IP {ip} (resolved from {parsed.hostname})")


class FederationClient:
    """HTTP client for ActivityPub server-to-server communication.

    Features:
    - HTTP Signature signing on outbound requests
    - SSRF prevention (blocks private/loopback/link-local IPs)
    - Exponential backoff retries
    - Configurable timeouts
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "iqoqo-federation/1.0",
                "Accept": "application/activity+json, application/ld+json",
            }
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(requests.ConnectionError),
        reraise=True,
    )
    def post_to_inbox(
        self,
        target_inbox_url: str,
        activity: dict[str, Any],
        sender_user_id: str,
        actor_key_id: str,
    ) -> requests.Response:
        """Deliver an activity to a remote actor's inbox.

        Args:
            target_inbox_url: The inbox URL to POST to.
            activity: The ActivityStreams activity JSON.
            sender_user_id: UUID of the local sender (for key lookup).
            actor_key_id: Full key ID URI for the Signature header.

        Returns:
            The HTTP response from the remote server.

        Raises:
            SSRFError: If the target URL resolves to a private IP.
            FederationDeliveryError: If delivery fails after retries.
        """
        _validate_url(target_inbox_url)

        import json

        body = json.dumps(activity).encode("utf-8")

        # Get private key for signing
        private_key = get_actor_private_key(sender_user_id)
        if not private_key:
            raise FederationDeliveryError(f"No private key for user {sender_user_id}")

        # Sign the request
        sig_headers = sign_request(
            method="POST",
            url=target_inbox_url,
            body=body,
            actor_key_id=actor_key_id,
            private_key=private_key,
        )

        headers = {
            "Content-Type": "application/activity+json",
            **sig_headers,
        }

        try:
            response = self._session.post(
                target_inbox_url,
                data=body,
                headers=headers,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise FederationDeliveryError(f"Failed to deliver to {target_inbox_url}: {exc}") from exc

        if response.status_code >= 400:
            raise FederationDeliveryError(f"Delivery to {target_inbox_url} returned {response.status_code}: {response.text[:200]}")

        return response

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.ConnectionError),
        reraise=True,
    )
    def fetch_actor(self, actor_uri: str) -> dict[str, Any]:
        """Fetch a remote actor's profile.

        Args:
            actor_uri: The actor's URI to fetch.

        Returns:
            The parsed JSON actor document.

        Raises:
            SSRFError: If the URI resolves to a private IP.
            FederationDeliveryError: If fetch fails.
        """
        _validate_url(actor_uri)

        try:
            response = self._session.get(
                actor_uri,
                headers={"Accept": "application/activity+json, application/ld+json"},
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            raise FederationDeliveryError(f"Failed to fetch actor {actor_uri}: {exc}") from exc

        if response.status_code != 200:
            raise FederationDeliveryError(f"Actor fetch {actor_uri} returned {response.status_code}")

        if len(response.content) > _MAX_RESPONSE_SIZE:
            raise FederationDeliveryError(f"Actor response too large: {len(response.content)} bytes")

        return response.json()  # type: ignore[no-any-return]

    def fetch_nodeinfo(self, domain: str) -> dict[str, Any] | None:
        """Fetch NodeInfo from a remote instance.

        Args:
            domain: The domain to query.

        Returns:
            Parsed NodeInfo JSON or None if not available.
        """
        well_known_url = f"https://{domain}/.well-known/nodeinfo"

        try:
            _validate_url(well_known_url)
        except SSRFError:
            return None

        try:
            response = self._session.get(
                well_known_url,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                allow_redirects=True,
            )
            if response.status_code != 200:
                return None

            links = response.json().get("links", [])
            nodeinfo_url = None
            for link in links:
                if "nodeinfo/2" in link.get("rel", ""):
                    nodeinfo_url = link.get("href")
                    break

            if not nodeinfo_url:
                return None

            _validate_url(nodeinfo_url)
            ni_response = self._session.get(
                nodeinfo_url,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
            )
            if ni_response.status_code == 200:
                return ni_response.json()  # type: ignore[no-any-return]
        except (requests.RequestException, SSRFError, ValueError):
            pass

        return None


# Module-level singleton
federation_client = FederationClient()
