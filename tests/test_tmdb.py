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

import os
from unittest.mock import MagicMock, patch

import pytest

from app.utils.tmdb import fetch_video_metadata


@patch.dict(os.environ, {"TMDB_API_KEY": "dummy_key"})
@patch("app.utils.tmdb.requests.get")
def test_fetch_video_metadata_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Inception",
                "overview": "A thief who steals corporate secrets...",
                "poster_path": "/poster.jpg",
                "release_date": "2010-07-15",
            }
        ]
    }
    mock_get.return_value = mock_resp

    result = fetch_video_metadata("0123456789")
    assert result["Title"] == "Inception"
    assert result["cover_url"] == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert result["Format"] == "video"


@patch.dict(os.environ, {}, clear=True)
def test_fetch_video_metadata_no_api_key():
    assert fetch_video_metadata("0123456789") is None
