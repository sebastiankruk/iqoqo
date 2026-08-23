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
from unittest.mock import Mock, patch

import defusedxml
import pytest
import requests

from app.utils.bgg import fetch_bgg_metadata
from app.utils.http_client import safe_get


def test_safe_get_http_timeout() -> None:
    """Verify safe_get properly passes and handles underlying HTTP timeouts."""
    with patch("requests.Session.get") as mock_get, patch("app.utils.http_client._resolve_with_timeout") as mock_resolve:
        mock_resolve.return_value = [[None, None, None, None, ["93.184.216.34"]]]
        mock_get.side_effect = requests.exceptions.Timeout("HTTP connection timed out")

        with pytest.raises(requests.exceptions.Timeout):
            safe_get("http://example.com", timeout=0.001)


def test_bgg_xxe_prevention() -> None:
    """Verify BGG parser correctly blocks XXE without successful exploitation."""
    xxe_payload = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>'

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.content = xxe_payload
        mock_response.text = xxe_payload.decode("utf-8")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        try:
            result = fetch_bgg_metadata("Catan")
            assert result is None
        except defusedxml.DefusedXmlException:
            pass
