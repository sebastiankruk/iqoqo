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

from unittest.mock import patch

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
