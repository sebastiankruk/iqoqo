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
"""Tests for AI sandbox egress filtering proxy logic and allowlisting."""

import asyncio
from pathlib import Path

import pytest

from deploy.sandbox_proxy.proxy import (
    is_destination_allowed,
    load_allowlist,
)

ALLOWLIST_PATH = Path(__file__).resolve().parent.parent / "deploy" / "sandbox_proxy" / "allowlist.conf"


def test_allowlist_conf_allows_gemini_oauth_and_avatars() -> None:
    """Verify production allowlist covers Gemini, OAuth, Antigravity, and profile avatars."""
    rules = load_allowlist(ALLOWLIST_PATH)
    assert len(rules) > 0

    assert is_destination_allowed("generativelanguage.googleapis.com", 443, rules)
    assert is_destination_allowed("accounts.google.com", 443, rules)
    assert is_destination_allowed("oauth2.googleapis.com", 443, rules)
    assert is_destination_allowed("cloudcode-pa.googleapis.com", 443, rules)
    assert is_destination_allowed("daily-cloudcode-pa.googleapis.com", 443, rules)
    assert is_destination_allowed("autopush-cloudcode-pa.sandbox.googleapis.com", 443, rules)
    assert is_destination_allowed("www.googleapis.com", 443, rules)
    assert is_destination_allowed("play.googleapis.com", 443, rules)
    assert is_destination_allowed("lh3.googleusercontent.com", 443, rules)
    assert is_destination_allowed("antigravity-unleash.goog", 443, rules)
    assert is_destination_allowed("antigravity.google", 443, rules)
    assert is_destination_allowed("fonts.gstatic.com", 443, rules)


def test_allowlist_blocks_unauthorized_destinations() -> None:
    """Verify allowlist blocks unauthorized external hosts, ports, and wildcard storage/forms."""
    rules = load_allowlist(ALLOWLIST_PATH)

    # Exfiltration vectors blocked (unauthenticated storage, forms, webhooks)
    assert not is_destination_allowed("storage.googleapis.com", 443, rules)
    assert not is_destination_allowed("docs.google.com", 443, rules)
    assert not is_destination_allowed("script.google.com", 443, rules)
    assert not is_destination_allowed("drive.google.com", 443, rules)
    assert not is_destination_allowed("googleapis.com", 443, rules)
    assert not is_destination_allowed("google.com", 443, rules)
    assert not is_destination_allowed("antigravity.google.com", 443, rules)
    assert not is_destination_allowed("other.googleusercontent.com", 443, rules)

    # Unauthorized domains
    assert not is_destination_allowed("evil.com", 443, rules)
    assert not is_destination_allowed("webhook.site", 443, rules)
    assert not is_destination_allowed("api.openai.com", 443, rules)
    assert not is_destination_allowed("github.com", 443, rules)

    # Unauthorized ports (even on allowed hosts)
    assert not is_destination_allowed("generativelanguage.googleapis.com", 80, rules)
    assert not is_destination_allowed("accounts.google.com", 8080, rules)

    # Internal / RFC1918 addresses
    assert not is_destination_allowed("127.0.0.1", 5000, rules)
    assert not is_destination_allowed("192.168.1.1", 443, rules)
    assert not is_destination_allowed("10.0.0.1", 443, rules)
    assert not is_destination_allowed("localhost", 5432, rules)


def test_load_allowlist_parses_file(tmp_path: Path) -> None:
    """Verify load_allowlist correctly parses configuration files."""
    conf_file = tmp_path / "test-allowlist.conf"
    conf_file.write_text(
        "# Comment line\ncustom.gemini.api:443\n*.google.internal:443\n\ncustom-default-port\n",
        encoding="utf-8",
    )

    rules = load_allowlist(conf_file)
    assert ("custom.gemini.api", 443) in rules
    assert ("*.google.internal", 443) in rules
    assert ("custom-default-port", 443) in rules

    assert is_destination_allowed("custom.gemini.api", 443, rules)
    assert is_destination_allowed("sub.google.internal", 443, rules)
    assert not is_destination_allowed("other.domain.com", 443, rules)


def test_load_allowlist_missing_file_fails_closed() -> None:
    """Verify load_allowlist fails closed (returns empty list) if file is missing."""
    rules = load_allowlist(Path("/nonexistent/path/to/allowlist.conf"))
    assert not rules
    # Everything should be blocked when rules list is empty
    assert not is_destination_allowed("generativelanguage.googleapis.com", 443, rules)
    assert not is_destination_allowed("accounts.google.com", 443, rules)


def test_proxy_blocks_unauthorized_connect_request() -> None:
    """Verify proxy actively returns 403 Forbidden for unauthorized destinations over socket."""
    from deploy.sandbox_proxy.proxy import handle_client

    rules = load_allowlist(ALLOWLIST_PATH)

    async def _runner() -> None:
        server = await asyncio.start_server(
            lambda r, w: handle_client(r, w, rules),
            host="127.0.0.1",
            port=0,
        )
        port = server.sockets[0].getsockname()[1]

        async with server:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            # Send blocked CONNECT request
            writer.write(b"CONNECT evil.com:443 HTTP/1.1\r\nHost: evil.com:443\r\n\r\n")
            await writer.drain()

            response = await reader.read(1024)
            writer.close()
            await writer.wait_closed()

            assert b"403 Forbidden" in response
            assert b"AI sandbox egress policy" in response

    asyncio.run(_runner())
