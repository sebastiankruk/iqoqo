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
    assert result["Format"] == "game"
