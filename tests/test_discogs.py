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

import os
from unittest.mock import patch, MagicMock
from app.utils.discogs import fetch_discogs_metadata

def test_fetch_discogs_metadata_uses_consumer_key_auth():
    """Test that Discogs lookup uses consumer key and secret when both are present."""
    with patch.dict(os.environ, {
        "DISCOGS_CONSUMER_KEY": "test_key",
        "DISCOGS_CONSUMER_SECRET": "test_secret",
        "DISCOGS_USER_TOKEN": "should_be_ignored"
    }):
        with patch("app.utils.discogs.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_get.return_value = mock_response
            
            fetch_discogs_metadata("123456789")
            
            # Verify headers
            args, kwargs = mock_get.call_args
            headers = kwargs.get("headers", {})
            assert headers["Authorization"] == "Discogs key=test_key, secret=test_secret"

def test_fetch_discogs_metadata_falls_back_to_legacy_token():
    """Test that Discogs lookup falls back to personal access token when consumer keys are missing."""
    with patch.dict(os.environ, {
        "DISCOGS_CONSUMER_KEY": "",
        "DISCOGS_CONSUMER_SECRET": "",
        "DISCOGS_USER_TOKEN": "test_token"
    }, clear=True):
        with patch("app.utils.discogs.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}
            mock_get.return_value = mock_response
            
            fetch_discogs_metadata("123456789")
            
            # Verify headers
            args, kwargs = mock_get.call_args
            headers = kwargs.get("headers", {})
            assert headers["Authorization"] == "Discogs token=test_token"

def test_fetch_discogs_metadata_returns_none_if_no_creds():
    """Test that Discogs lookup returns None immediately if no credentials are configured."""
    with patch.dict(os.environ, {
        "DISCOGS_CONSUMER_KEY": "",
        "DISCOGS_CONSUMER_SECRET": "",
        "DISCOGS_USER_TOKEN": ""
    }, clear=True):
        result = fetch_discogs_metadata("123456789")
        assert result is None
