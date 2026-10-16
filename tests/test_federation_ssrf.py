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
"""Tests for SSRF prevention in outbound FederationClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.federation_client import FederationClient
from app.utils.http_client import SSRFError


class TestFederationSSRF:
    """Test suite ensuring FederationClient blocks private, loopback, and metadata IPs."""

    @pytest.mark.parametrize(
        "restricted_url",
        [
            "http://127.0.0.1/actor",
            "http://127.0.0.2:8000/actor",
            "http://localhost/actor",
            "http://10.0.0.1/actor",
            "http://10.254.0.1/inbox",
            "http://172.16.0.1/actor",
            "http://172.31.255.255/actor",
            "http://192.168.0.1/actor",
            "http://192.168.1.100/inbox",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/actor",
        ],
    )
    def test_fetch_actor_blocks_restricted_ips(self, restricted_url: str):
        client = FederationClient()
        with pytest.raises(SSRFError):
            client.fetch_actor(restricted_url)

    @pytest.mark.parametrize(
        "restricted_inbox",
        [
            "http://127.0.0.1/inbox",
            "http://192.168.1.1/inbox",
            "http://10.0.0.1/inbox",
            "http://169.254.169.254/inbox",
        ],
    )
    def test_post_to_inbox_blocks_restricted_ips(self, restricted_inbox: str):
        client = FederationClient()
        with pytest.raises(SSRFError):
            client.post_to_inbox(restricted_inbox, {"type": "Follow"})

    @patch("app.core.federation_client.safe_get")
    def test_fetch_actor_success_with_public_ip(self, mock_safe_get, app):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "https://remote-fed.example.com/users/carol",
            "type": "Person",
            "preferredUsername": "carol",
            "inbox": "https://remote-fed.example.com/users/carol/inbox",
            "publicKey": {
                "id": "https://remote-fed.example.com/users/carol#main-key",
                "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIB...",
            },
        }
        mock_safe_get.return_value = mock_response

        with app.app_context():
            client = FederationClient()
            data = client.fetch_actor("https://remote-fed.example.com/users/carol")

            assert data is not None
            assert data["preferredUsername"] == "carol"
            assert data["id"] == "https://remote-fed.example.com/users/carol"

    @patch("app.core.federation_client.safe_post")
    def test_post_to_inbox_success(self, mock_safe_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_safe_post.return_value = mock_resp

        client = FederationClient()
        activity = {"type": "Create", "object": "https://example.com/books/1"}
        resp = client.post_to_inbox("https://remote-fed.example.com/inbox", activity)

        assert resp.status_code == 202
        mock_safe_post.assert_called_once()
