"""Tests for BoardGameGeek2 migration, rate-limiting backoff, and lookup strategy."""

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

from unittest.mock import MagicMock, patch

import boardgamegeek.utils
import defusedxml.ElementTree as ET
import pytest
import requests
from boardgamegeek.exceptions import BoardGameGeekError

from app.strategies.boardgame import BoardGameLookupStrategy
from app.utils.bgg import BGGBackoffAdapter, fetch_bgg_metadata, get_bgg_client


def test_bgg_uses_defused_xml():
    """Verify boardgamegeek library is configured with defusedxml."""
    get_bgg_client()
    assert boardgamegeek.utils.ET is ET


def test_bgg_429_backoff_adapter_retries_and_succeeds():
    """WHEN BGG API returns HTTP 429 Too Many Requests, client waits with exponential backoff and retries up to 3 times."""
    adapter = BGGBackoffAdapter(max_retries=3, backoff_factor=0.01)

    mock_req = MagicMock()

    resp_429_1 = requests.Response()
    resp_429_1.status_code = 429

    resp_429_2 = requests.Response()
    resp_429_2.status_code = 429

    resp_200 = requests.Response()
    resp_200.status_code = 200

    with (
        patch("requests.adapters.HTTPAdapter.send", side_effect=[resp_429_1, resp_429_2, resp_200]) as mock_super_send,
        patch.object(adapter, "_sleep") as mock_sleep,
    ):
        result = adapter.send(mock_req)
        assert result.status_code == 200
        assert mock_super_send.call_count == 3
        assert mock_sleep.call_count == 2
        # Backoff delays: 0.01 * 1 = 0.01, 0.01 * 2 = 0.02
        mock_sleep.assert_any_call(0.01)
        mock_sleep.assert_any_call(0.02)


def test_bgg_429_backoff_adapter_exhausts_retries():
    """When BGG returns 429 repeatedly, retries are exhausted after max_retries."""
    adapter = BGGBackoffAdapter(max_retries=3, backoff_factor=0.01)
    mock_req = MagicMock()

    resp_429 = requests.Response()
    resp_429.status_code = 429

    with (
        patch("requests.adapters.HTTPAdapter.send", return_value=resp_429) as mock_super_send,
        patch.object(adapter, "_sleep") as mock_sleep,
    ):
        result = adapter.send(mock_req)
        assert result.status_code == 429
        assert mock_super_send.call_count == 4  # Initial + 3 retries
        assert mock_sleep.call_count == 3


@patch("app.utils.bgg.get_bgg_client")
def test_fetch_bgg_metadata_via_client_success(mock_get_client):
    """Test fetching metadata using boardgamegeek client object mapping."""
    mock_game = MagicMock()
    mock_game.id = 13
    mock_game.name = "Catan"
    mock_game.description = "Trade, build, settle"
    mock_game.image = "https://example.com/catan.jpg"
    mock_game.thumbnail = "https://example.com/catan_thumb.jpg"
    mock_game.mechanics = ["Trading", "Dice Rolling"]
    mock_game.designers = ["Klaus Teuber"]
    mock_game.min_players = 3
    mock_game.max_players = 4
    mock_game.playing_time = 90
    mock_game.year = 1995
    mock_game._data = {"raw": "test"}

    mock_client = MagicMock()
    mock_client.game.return_value = mock_game
    mock_get_client.return_value = mock_client

    result = fetch_bgg_metadata("Catan")
    assert result is not None
    assert result["Title"] == "Catan"
    assert result["cover_url"] == "https://example.com/catan.jpg"
    assert result["bgg_id"] == "13"
    assert result["PublicationYear"] == "1995"
    assert result["Mechanics"] == ["Trading", "Dice Rolling"]
    assert result["Designers"] == ["Klaus Teuber"]
    assert result["author"] == "Klaus Teuber"
    assert result["Format"] == "boardgame"
    assert result["Source"] == "BGG"
    assert result["min_players"] == 3
    assert result["max_players"] == 4
    assert result["playing_time"] == 90
    mock_client.game.assert_called_once_with(name="Catan")


@patch("app.utils.bgg.get_bgg_client")
def test_fetch_bgg_metadata_numeric_id(mock_get_client):
    """Test fetching metadata by numeric BGG ID."""
    mock_game = MagicMock()
    mock_game.id = 13
    mock_game.name = "Catan"
    mock_game.description = ""
    mock_game.image = None
    mock_game.thumbnail = None
    mock_game.mechanics = []
    mock_game.designers = []
    mock_game.min_players = None
    mock_game.max_players = None
    mock_game.playing_time = None
    mock_game.year = None
    mock_game._data = {}

    mock_client = MagicMock()
    mock_client.game.return_value = mock_game
    mock_get_client.return_value = mock_client

    result = fetch_bgg_metadata("13")
    assert result is not None
    assert result["bgg_id"] == "13"
    assert result["Title"] == "Catan"
    mock_client.game.assert_called_once_with(game_id=13)


@patch("app.utils.bgg.get_bgg_client")
def test_fetch_bgg_metadata_not_found(mock_get_client):
    """Test fetching metadata when game is not found."""
    mock_client = MagicMock()
    mock_client.game.return_value = None
    mock_get_client.return_value = mock_client

    result = fetch_bgg_metadata("NonexistentBoardGame999999")
    assert result is None


@patch("app.utils.bgg.get_bgg_client")
def test_fetch_bgg_metadata_handles_client_error(mock_get_client):
    """Test graceful handling of BoardGameGeekError."""
    mock_client = MagicMock()
    mock_client.game.side_effect = BoardGameGeekError("Rate limit or API failure")
    mock_get_client.return_value = mock_client

    result = fetch_bgg_metadata("Catan")
    assert result is None


def test_boardgame_lookup_strategy_short_numeric():
    """Test that BoardGameLookupStrategy routes short numeric barcode directly to BGG."""
    strategy = BoardGameLookupStrategy()
    with patch("app.strategies.boardgame.fetch_bgg_metadata") as mock_fetch:
        mock_fetch.return_value = {"Title": "Catan", "bgg_id": "13"}
        meta, provider = strategy.lookup("13")
        assert provider == "bgg"
        assert meta["data_source"] == "bgg"
        assert meta["Title"] == "Catan"
        mock_fetch.assert_called_once_with("13")


def test_boardgame_lookup_strategy_query_fallback():
    """Test that BoardGameLookupStrategy falls back to query when barcode lookup yields nothing."""
    strategy = BoardGameLookupStrategy()

    def mock_fetch(q):
        if q == "Terraforming Mars":
            return {"Title": "Terraforming Mars"}
        return None

    with (
        patch("app.strategies.boardgame.resolve_physical_media", return_value=None),
        patch("app.strategies.boardgame.fetch_bgg_metadata", side_effect=mock_fetch) as mock_bgg,
    ):
        meta, provider = strategy.lookup("999999999999", query="Terraforming Mars")
        assert provider == "bgg"
        assert meta["Title"] == "Terraforming Mars"
        mock_bgg.assert_any_call("Terraforming Mars")
