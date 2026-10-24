"""Tests for Twitch/IGDB 4-state health reporting and system status."""

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

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.utils.igdb import _TOKEN_FILE, get_igdb_token_status


@pytest.fixture(autouse=True)
def clean_token_file():
    """Ensure token file is cleaned up before and after tests."""
    if os.path.exists(_TOKEN_FILE):
        os.remove(_TOKEN_FILE)
    yield
    if os.path.exists(_TOKEN_FILE):
        os.remove(_TOKEN_FILE)


def test_igdb_health_disabled_when_unconfigured():
    """State 1: DISABLED when neither client ID nor secret is configured."""
    with patch.dict(os.environ, {}, clear=True):
        # Ensure env does not have IGDB/TWITCH keys
        status = get_igdb_token_status()
        assert status["status"] == "DISABLED"
        assert status["configured"] is False
        assert status["active"] is False
        assert status["reason"] == "missing_credentials"


@patch.dict(os.environ, {"TWITCH_CLIENT_ID": "dummy_client", "TWITCH_CLIENT_SECRET": "dummy_secret"})
def test_igdb_health_configured_valid_when_token_active():
    """State 2: CONFIGURED_VALID when credentials set and cached token is fresh."""
    with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"access_token": "valid_token", "expires_in": 7200}, f)

    status = get_igdb_token_status()
    assert status["status"] == "CONFIGURED_VALID"
    assert status["configured"] is True
    assert status["active"] is True
    assert status["token_age_hours"] is not None
    assert status["reason"] == "token_valid"


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
def test_igdb_health_expired_needs_refresh_when_cached_token_stale():
    """State 3: EXPIRED_NEEDS_REFRESH when cached token is past expires_in and probe_remote=False."""
    with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump({"access_token": "stale_token", "expires_in": 3600}, f)

    # Simulate token created 4000 seconds ago
    with patch("time.time", return_value=time.time() + 4000):
        status = get_igdb_token_status(probe_remote=False)
        assert status["status"] == "EXPIRED_NEEDS_REFRESH"
        assert status["configured"] is True
        assert status["active"] is False
        assert status["reason"] == "token_expired"


@patch.dict(os.environ, {"IGDB_CLIENT_ID": "dummy_client", "IGDB_CLIENT_SECRET": "dummy_secret"})
def test_igdb_health_expired_needs_refresh_when_no_token_cached():
    """State 3: EXPIRED_NEEDS_REFRESH when credentials configured but no token file exists."""
    status = get_igdb_token_status(probe_remote=False)
    assert status["status"] == "EXPIRED_NEEDS_REFRESH"
    assert status["configured"] is True
    assert status["active"] is False
    assert status["reason"] == "token_missing"


@patch.dict(os.environ, {"TWITCH_CLIENT_ID": "bad_client", "TWITCH_CLIENT_SECRET": "bad_secret"})
@patch("app.utils.igdb.requests.post")
def test_igdb_health_auth_error_on_invalid_credentials(mock_post):
    """State 4: AUTH_ERROR when Twitch OAuth endpoint returns 401 or 400."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "invalid client"
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized", response=mock_resp)
    mock_post.return_value = mock_resp

    status = get_igdb_token_status(probe_remote=True)
    assert status["status"] == "AUTH_ERROR"
    assert status["configured"] is True
    assert status["active"] is False
    mock_post.assert_called_once()


@patch.dict(os.environ, {"TWITCH_CLIENT_ID": "dummy_client", "TWITCH_CLIENT_SECRET": "dummy_secret"})
@patch("app.utils.igdb.requests.post")
def test_igdb_health_probe_remote_refreshes_token(mock_post):
    """Probe remote successfully refreshes expired token to CONFIGURED_VALID."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "fresh_token", "expires_in": 3600}
    mock_post.return_value = mock_resp

    status = get_igdb_token_status(probe_remote=True)
    assert status["status"] == "CONFIGURED_VALID"
    assert status["configured"] is True
    assert status["active"] is True
    assert status["reason"] == "token_refreshed"


def test_system_status_endpoint_reports_all_integrations(client, normal_user_headers):
    """GET /api/system/status reports Allegro, IGDB 4-state, and BGG integrations."""
    response = client.get("/api/system/status", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True

    payload = data["data"]
    assert "allegro" in payload
    assert "igdb" in payload
    assert "twitch_igdb_status" in payload
    assert payload["twitch_igdb_status"] in ("DISABLED", "CONFIGURED_VALID", "EXPIRED_NEEDS_REFRESH", "AUTH_ERROR")
    assert "bgg" in payload
    assert "configured" in payload["bgg"]
    assert payload["bgg"]["status"] in ("CONFIGURED_VALID", "DISABLED")
