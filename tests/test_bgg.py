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

from app.utils.bgg import fetch_bgg_metadata


@patch("app.utils.bgg.requests.get")
def test_fetch_bgg_metadata_success(mock_get):
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
        </item>
    </items>"""

    mock_get.side_effect = [mock_search_resp, mock_thing_resp]

    result = fetch_bgg_metadata("Catan")

    assert result["Title"] == "Catan"
    assert result["cover_url"] == "http://bgg.com/image.jpg"
    assert "Trading" in result["Mechanics"]
    assert result["Format"] == "boardgame"


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
