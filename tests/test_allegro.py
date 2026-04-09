# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from unittest.mock import patch

from app.utils.allegro import fetch_allegro_metadata, get_allegro_token


@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_success(mock_post):
    """Test successful Allegro OAuth2 token retrieval."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "mock_access_token_123"}

    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
        token = get_allegro_token()
        assert token == "mock_access_token_123"
        mock_post.assert_called_once()


@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_failure(mock_post):
    """Test Allegro OAuth2 token retrieval failure."""
    mock_post.return_value.status_code = 401

    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
        token = get_allegro_token()
        assert token is None


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.requests.get")
def test_fetch_allegro_metadata_success(mock_get, mock_token):
    """Test successful Allegro product metadata fetch."""
    mock_token.return_value = "valid_token"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "products": [
            {
                "name": "The Matrix [Blu-ray]",
                "images": [{"url": "http://allegro.img/matrix.jpg"}],
                "description": "Epic Sci-Fi Movie",
                "publication": {"publisher": "Warner Home Video"},
            }
        ]
    }

    result = fetch_allegro_metadata("5900012345678")

    assert result is not None
    assert result["title"] == "The Matrix [Blu-ray]"
    assert result["cover_url"] == "http://allegro.img/matrix.jpg"
    assert result["source"] == "Allegro"
    assert "listing?string=5900012345678" in result["affiliate_url"]


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.requests.get")
def test_fetch_allegro_metadata_no_results(mock_get, mock_token):
    """Test Allegro product metadata fetch with no results."""
    mock_token.return_value = "valid_token"
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"products": []}

    result = fetch_allegro_metadata("0000000000000")
    assert result is None
