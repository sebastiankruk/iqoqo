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

import pytest
import requests

from app.utils.bgg import clean_bgg_query, fetch_bgg_metadata


@patch("app.utils.bgg.requests.get")
@patch("app.utils.bgg.os.getenv")
def test_fetch_bgg_metadata_success(mock_getenv, mock_get):
    mock_getenv.return_value = "fake_token"
    # Mock search endpoint response
    mock_search_resp = MagicMock()
    mock_search_resp.content = b'<?xml version="1.0" encoding="utf-8"?><items><item id="12345"></item></items>'

    # Mock details endpoint response
    mock_thing_resp = MagicMock()
    mock_thing_resp.content = b"""<?xml version="1.0" encoding="utf-8"?>
    <items>
        <item id="12345">
            <name type="primary" value="Catan" />
            <description>Trading game</description>
            <image>http://bgg.com/image.jpg</image>
            <link type="boardgamemechanic" value="Trading" />
            <minplayers value="3" />
            <maxplayers value="4" />
            <playingtime value="120" />
            <yearpublished value="1995" />
        </item>
    </items>"""

    mock_get.side_effect = [mock_search_resp, mock_thing_resp]

    result = fetch_bgg_metadata("Catan")

    assert result["Title"] == "Catan"
    assert result["cover_url"] == "http://bgg.com/image.jpg"
    assert "Trading" in result["Mechanics"]
    assert result["Format"] == "boardgame"
    assert result["min_players"] == 3
    assert result["max_players"] == 4
    assert result["playing_time"] == 120
    assert result["PublicationYear"] == "1995"
    assert result["bgg_id"] == "12345"
    assert result["Source"] == "BGG"

    # Check if authorization header was passed
    call_args = mock_get.call_args_list[0]
    assert call_args[1]["headers"]["Authorization"] == "Bearer fake_token"


@patch("app.utils.bgg.requests.get")
def test_fetch_bgg_metadata_with_designers(mock_get):
    """Test that BGG metadata includes designer information."""
    # Mock search endpoint response
    mock_search_resp = MagicMock()
    mock_search_resp.content = b'<?xml version="1.0" encoding="utf-8"?><items><item id="13"></item></items>'

    # Mock details endpoint response with designers
    mock_thing_resp = MagicMock()
    mock_thing_resp.content = b"""<?xml version="1.0" encoding="utf-8"?>
    <items>
        <item id="13">
            <name type="primary" value="Catan" />
            <description>Trading and building game</description>
            <link type="boardgamemechanic" value="Trading" />
            <link type="boardgamemechanic" value="Hexagon Grid" />
            <link type="boardgamedesigner" value="Klaus Teuber" />
        </item>
    </items>"""

    mock_get.side_effect = [mock_search_resp, mock_thing_resp]

    result = fetch_bgg_metadata("Catan")

    assert result["Title"] == "Catan"
    assert "Trading" in result["Mechanics"]
    assert "Hexagon Grid" in result["Mechanics"]
    assert "Klaus Teuber" in result.get("Designers", [])


def test_clean_bgg_query():
    """Test parenthetical content removal from BGG queries."""
    assert clean_bgg_query("Brass: Birmingham (2018)") == "Brass: Birmingham"
    assert clean_bgg_query("Catan [Fifth Edition]") == "Catan"
    assert clean_bgg_query("Pandemic (Big Box) (2015)") == "Pandemic"
    assert clean_bgg_query("No Parenthesis") == "No Parenthesis"
    assert clean_bgg_query("") == ""


@patch("app.utils.bgg.os.getenv")
@patch("app.utils.bgg.logger")
def test_fetch_bgg_metadata_no_token_warning(mock_logger, mock_getenv):
    """Test that a warning is logged when BGG_API_TOKEN is missing."""
    mock_getenv.return_value = None
    # We don't care about the return value, just the side effect of logging
    with patch("app.utils.bgg.requests.get") as mock_get:
        mock_get.return_value.status_code = 401
        mock_get.return_value.raise_for_status.side_effect = requests.RequestException("Unauthorized")
        fetch_bgg_metadata("Catan")

    mock_logger.warning.assert_any_call(
        "BGG_API_TOKEN not found in environment. BoardGameGeek lookups will likely result in 401 Unauthorized."
    )


@patch("app.utils.bgg.requests.get")
def test_fetch_bgg_metadata_xml_parse_error(mock_get):
    """Test graceful handling of malformed XML from BGG."""
    mock_resp = MagicMock()
    mock_resp.content = b"not xml"
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    result = fetch_bgg_metadata("Catan")
    assert result is None
