"""Tests for the IGDB metadata fetching utility."""

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

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.utils.igdb import fetch_game_metadata, get_igdb_token


@pytest.fixture(autouse=True)
def clean_token_file():
    """Ensure token file is cleaned up before and after tests."""
    from app.utils.igdb import _TOKEN_FILE

    if os.path.exists(_TOKEN_FILE):
        os.remove(_TOKEN_FILE)
    yield
    if os.path.exists(_TOKEN_FILE):
        os.remove(_TOKEN_FILE)


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.requests.post")
def test_get_igdb_token_success(mock_post):
    """Test getting an IGDB token successfully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "mocked_token", "expires_in": 360000}
    mock_post.return_value = mock_resp

    token = get_igdb_token()
    assert token == "mocked_token"
    mock_post.assert_called_once()

    # Call again, should load from cache file without posting again
    token_cached = get_igdb_token()
    assert token_cached == "mocked_token"
    assert mock_post.call_count == 1  # Should still be 1


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.requests.post")
def test_get_igdb_token_refresh_on_expiry(mock_post):
    """Test that a new token is fetched if the cached one is expired or close to expiration."""
    # Write a token to the cache file that expires soon
    from app.utils.igdb import _TOKEN_FILE

    cached_data = {"access_token": "old_token", "expires_in": 3600}
    with open(_TOKEN_FILE, "w", encoding="utf-8") as wf:
        json.dump(cached_data, wf)

    # Mock time.time to simulate expiration
    # File mtime is current time. If we query 4000 seconds later, it should be expired.
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}
    mock_post.return_value = mock_resp

    with patch("app.utils.igdb.time.time", return_value=time.time() + 4000):
        token = get_igdb_token()
        assert token == "new_token"
        mock_post.assert_called_once()


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.get_igdb_token", return_value="mocked_token")
@patch("app.utils.igdb.requests.post")
def test_fetch_game_metadata_success(mock_post, mock_get_token):
    """Test fetching game metadata successfully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": 1234,
            "name": "The Witcher 3: Wild Hunt",
            "summary": "An open world RPG.",
            "first_release_date": 1431993600,  # May 19, 2015
            "cover": {"id": 5678, "url": "//images.igdb.com/igdb/image/upload/t_thumb/co1r3q.jpg"},
        }
    ]
    mock_post.return_value = mock_resp

    meta = fetch_game_metadata("Witcher 3")
    assert meta is not None
    assert meta["title"] == "The Witcher 3: Wild Hunt"
    assert meta["PublicationYear"] == 2015
    assert meta["cover_url"] == "https://images.igdb.com/igdb/image/upload/t_cover_big/co1r3q.jpg"
    assert meta["Source"] == "IGDB"
    assert meta["Format"] == "game"

    mock_post.assert_called_once()
    headers = mock_post.call_args[1]["headers"]
    assert headers["Client-ID"] == "dummy_client"
    assert headers["Authorization"] == "Bearer mocked_token"


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.get_igdb_token", return_value="mocked_token")
@patch("app.utils.igdb.requests.post")
def test_fetch_game_metadata_no_results(mock_post, mock_get_token):
    """Test fetching metadata when no game is found."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []
    mock_post.return_value = mock_resp

    meta = fetch_game_metadata("NonexistentGame12345")
    assert meta is None


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.requests.post")
def test_get_igdb_token_auth_failure(mock_post):
    """Test Twitch API authentication failure."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
    mock_post.return_value = mock_resp

    token = get_igdb_token()
    assert token is None


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.get_igdb_token", return_value="mocked_token")
@patch("app.utils.igdb.requests.post")
def test_fetch_game_metadata_network_error(mock_post, mock_get_token):
    """Test fetching game metadata handling network errors."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    meta = fetch_game_metadata("Witcher 3")
    assert meta is None

