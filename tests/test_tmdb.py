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
