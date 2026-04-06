from unittest.mock import patch

import pytest

from app.utils.upc import fetch_upc_metadata


@patch("app.utils.upc.requests.get")
def test_fetch_upc_metadata_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "items": [
            {"title": "Starry Night 1000pc", "upc": "4005556199999", "brand": "Ravensburger", "images": ["http://example.com/cover.jpg"]}
        ]
    }

    result = fetch_upc_metadata("4005556199999")

    assert result is not None
    assert result["title"] == "Starry Night 1000pc"
    assert result["manufacturer"] == "Ravensburger"
    assert result["format"] == "puzzle"


@patch("app.utils.upc.requests.get")
def test_fetch_upc_metadata_not_found(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"items": []}

    result = fetch_upc_metadata("0000000000000")
    assert result is None
