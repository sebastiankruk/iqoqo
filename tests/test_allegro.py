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
from unittest.mock import MagicMock, mock_open, patch

from app.utils.allegro import fetch_allegro_metadata, get_allegro_token


@patch("os.path.isfile")
@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_client_credentials(mock_post, mock_isfile):
    """Test successful Allegro Client Credentials token retrieval (Fallback)."""
    mock_isfile.return_value = False
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "mock_client_token"}

    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
        token = get_allegro_token()
        assert token == "mock_client_token"


@patch("os.path.isfile")
@patch("os.path.getmtime")
def test_get_allegro_token_from_file_valid(mock_mtime, mock_isfile):
    """Test loading valid Allegro token from file (User Context)."""
    mock_isfile.return_value = True
    mock_mtime.return_value = 1000000000  # way in the future or recent enough

    # Mock current time to be close to mtime
    with patch("time.time", return_value=1000000000 + 100):
        mock_json = '{"access_token": "file_token", "refresh_token": "ref_123"}'
        with patch("builtins.open", mock_open(read_data=mock_json)):
            with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
                token = get_allegro_token()
                assert token == "file_token"


@patch("os.path.isfile")
@patch("os.path.getmtime")
@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_refresh(mock_post, mock_mtime, mock_isfile):
    """Test refreshing Allegro token when file is old."""
    mock_isfile.return_value = True
    mock_mtime.return_value = 1000000000

    # Mock current time to be > 11 hours later
    with patch("time.time", return_value=1000000000 + (12 * 3600)):
        mock_json = '{"access_token": "old_token", "refresh_token": "ref_123"}'
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "new_token", "refresh_token": "ref_new"}

        with patch("builtins.open", mock_open(read_data=mock_json)):
            with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
                token = get_allegro_token()
                assert token == "new_token"
                mock_post.assert_called_once()


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.requests.get")
@patch("os.path.isfile")
def test_fetch_allegro_metadata_catalog_success(mock_isfile, mock_get, mock_token):
    """Test successful Allegro product metadata fetch from Catalog."""
    mock_token.return_value = "valid_token"
    mock_isfile.return_value = True  # Enable catalog search
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
    assert result["source"] == "Allegro Catalog"


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.requests.get")
@patch("os.path.isfile")
def test_fetch_allegro_metadata_listing_fallback(mock_isfile, mock_get, mock_token):
    """Test fallback to Listing when Catalog returns no results."""
    mock_token.return_value = "valid_token"
    mock_isfile.return_value = True

    # First response (Catalog) empty, second (Listing) success
    catalog_resp = MagicMock()
    catalog_resp.status_code = 200
    catalog_resp.json.return_value = {"products": []}

    listing_resp = MagicMock()
    listing_resp.status_code = 200
    listing_resp.json.return_value = {"items": {"regular": [{"name": "Listing Item", "images": [{"url": "http://img.jpg"}]}]}}

    mock_get.side_effect = [catalog_resp, listing_resp]

    result = fetch_allegro_metadata("5900012345678")

    assert result is not None
    assert result["title"] == "Listing Item"
    assert result["source"] == "Allegro Listing"


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.requests.get")
@patch("os.path.isfile")
def test_fetch_allegro_metadata_catalog_with_client_credentials_only(mock_isfile, mock_get, mock_token):
    """Verify Catalog search works natively when token file is missing (Client Credentials flow)."""
    mock_token.return_value = "client_credentials_token"
    mock_isfile.return_value = False  # Token file is explicitly missing!
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "products": [
            {
                "name": "Hardened Fallback Media",
                "images": [{"url": "http://allegro.img/fallback.jpg"}],
                "description": "Seamless client credential catalog fetch",
                "publication": {"publisher": "Fallback Publisher"},
            }
        ]
    }

    result = fetch_allegro_metadata("9788301000003")

    assert result is not None
    assert result["title"] == "Hardened Fallback Media"
    assert result["source"] == "Allegro Catalog"
    # Step 2 (Listing API) must not be triggered if file token is absent
    assert mock_get.call_count == 1
