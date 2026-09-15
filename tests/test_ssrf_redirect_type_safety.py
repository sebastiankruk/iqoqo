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

"""Tests for SSRF redirect handler type safety."""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.http_client import SSRFError, safe_get


class CustomLocationHeader:
    """Mock location header object to test string coercion."""

    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value


def test_safe_get_redirect_type_safety() -> None:
    """Verifies that safe_get coerces non-string redirect headers to str without raising TypeError."""
    mock_resp_1 = MagicMock()
    mock_resp_1.is_redirect = True
    mock_resp_1.headers = {"location": CustomLocationHeader("http://example.com/target")}

    mock_resp_2 = MagicMock()
    mock_resp_2.is_redirect = False
    mock_resp_2.status_code = 200

    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]
        with patch("requests.Session.get", side_effect=[mock_resp_1, mock_resp_2]):
            res = safe_get("http://example.com/initial")
            assert res is mock_resp_2


def test_covers_google_books_uses_safe_get() -> None:
    """Ensure Google Books search in fetch_external_api_cover uses safe_get and handles SSRFError."""
    from app.utils.covers import fetch_external_api_cover

    with patch("app.utils.covers.download_direct_url", return_value=None), patch("app.utils.covers.safe_get") as mock_safe_get:
        mock_safe_get.side_effect = SSRFError("Blocked private IP")
        res = fetch_external_api_cover("9780441569595")
        assert res is None
        # safe_get was invoked for the Google Books endpoint
        assert mock_safe_get.called
        call_url = mock_safe_get.call_args[0][0]
        assert "googleapis.com" in call_url


def test_covers_musicbrainz_uses_safe_get() -> None:
    """Ensure _fetch_musicbrainz_cover uses safe_get and handles SSRFError."""
    from app.utils.covers import _fetch_musicbrainz_cover

    with patch("app.utils.covers.safe_get") as mock_safe_get:
        mock_safe_get.side_effect = SSRFError("Blocked private IP")
        res = _fetch_musicbrainz_cover("123456789012")
        assert res is None
        assert mock_safe_get.called
        call_url = mock_safe_get.call_args[0][0]
        assert "musicbrainz.org" in call_url
