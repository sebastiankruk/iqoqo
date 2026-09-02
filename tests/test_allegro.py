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

from app.config import Config
from app.utils.allegro import (
    exchange_device_token,
    fetch_allegro_metadata,
    get_allegro_token,
    get_allegro_token_status,
    has_allegro_user_token,
    load_allegro_token,
    save_allegro_token,
)


@patch("app.utils.allegro.load_allegro_token")
@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_client_credentials(mock_post, mock_load):
    """Test successful Allegro Client Credentials token retrieval (Fallback when no user token)."""
    mock_load.return_value = None
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "mock_client_token"}

    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
        token = get_allegro_token()
        assert token == "mock_client_token"
        mock_post.assert_called_once()
        called_headers = mock_post.call_args[1].get("headers")
        assert called_headers is not None
        assert "User-Agent" in called_headers
        assert called_headers["User-Agent"].startswith(Config.ALLEGRO_APP_NAME + "/")


@patch("app.utils.allegro.load_allegro_token")
def test_get_allegro_token_from_cache_valid(mock_load):
    """Test loading valid Allegro token from central storage (User Context)."""
    mock_load.return_value = {
        "access_token": "cache_token",
        "refresh_token": "ref_123",
        "created_at": 1000000000,
    }

    with patch("time.time", return_value=1000000000 + 100):
        with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
            token = get_allegro_token()
            assert token == "cache_token"


@patch("app.utils.allegro.save_allegro_token")
@patch("app.utils.allegro.load_allegro_token")
@patch("app.utils.allegro.requests.post")
def test_get_allegro_token_refresh(mock_post, mock_load, mock_save):
    """Test refreshing Allegro token when cached token is old."""
    mock_load.return_value = {
        "access_token": "old_token",
        "refresh_token": "ref_123",
        "created_at": 1000000000,
    }

    with patch("time.time", return_value=1000000000 + (12 * 3600)):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "new_token", "refresh_token": "ref_new"}

        with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_secret"}):
            token = get_allegro_token()
            assert token == "new_token"
            mock_post.assert_called_once()
            mock_save.assert_called_once()
            called_headers = mock_post.call_args[1].get("headers")
            assert called_headers is not None
            assert "User-Agent" in called_headers
            assert called_headers["User-Agent"].startswith(Config.ALLEGRO_APP_NAME + "/")


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.has_allegro_user_token")
@patch("app.utils.allegro.requests.get")
def test_fetch_allegro_metadata_catalog_success(mock_get, mock_has_user, mock_token):
    """Test successful Allegro product metadata fetch from Catalog."""
    mock_token.return_value = "valid_token"
    mock_has_user.return_value = True
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
    mock_get.assert_called_once()
    called_headers = mock_get.call_args[1].get("headers")
    assert called_headers is not None
    assert "User-Agent" in called_headers
    assert called_headers["User-Agent"].startswith(Config.ALLEGRO_APP_NAME + "/")


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.has_allegro_user_token")
@patch("app.utils.allegro.requests.get")
def test_fetch_allegro_metadata_listing_fallback(mock_get, mock_has_user, mock_token):
    """Test fallback to Listing when Catalog returns no results."""
    mock_token.return_value = "valid_token"
    mock_has_user.return_value = True

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
    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        called_headers = call[1].get("headers")
        assert called_headers is not None
        assert "User-Agent" in called_headers
        assert called_headers["User-Agent"].startswith(Config.ALLEGRO_APP_NAME + "/")


@patch("app.utils.allegro.get_allegro_token")
@patch("app.utils.allegro.has_allegro_user_token")
@patch("app.utils.allegro.requests.get")
def test_fetch_allegro_metadata_catalog_with_client_credentials_only(mock_get, mock_has_user, mock_token):
    """Verify Catalog search works natively when user token is absent (Client Credentials flow)."""
    mock_token.return_value = "client_credentials_token"
    mock_has_user.return_value = False
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
    assert mock_get.call_count == 1
    called_headers = mock_get.call_args[1].get("headers")
    assert called_headers is not None
    assert "User-Agent" in called_headers
    assert called_headers["User-Agent"].startswith(Config.ALLEGRO_APP_NAME + "/")


@patch("app.utils.allegro.save_allegro_token")
@patch("app.utils.allegro.requests.post")
def test_exchange_device_token_saves_to_cache(mock_post, mock_save):
    """Verify exchange_device_token saves retrieved tokens to central store."""
    mock_post.return_value.ok = True
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "access_token": "exchanged_acc_tok",
        "refresh_token": "exchanged_ref_tok",
    }

    res = exchange_device_token("dev_code_123", "client_1", "secret_1")
    assert res.get("access_token") == "exchanged_acc_tok"
    mock_save.assert_called_once_with(
        {
            "access_token": "exchanged_acc_tok",
            "refresh_token": "exchanged_ref_tok",
        }
    )


@patch("app.utils.allegro.load_allegro_token")
def test_get_allegro_token_status(mock_load):
    """Verify get_allegro_token_status across multiple configurations."""
    # 1. Missing credentials
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "", "ALLEGRO_CLIENT_SECRET": ""}, clear=True):
        with patch("app.db.models.InstanceSettings.get_value", return_value=None):
            st = get_allegro_token_status()
            assert st["configured"] is False
            assert st["allegro_token_active"] is False
            assert st["reason"] == "missing_credentials"

    # 2. Configured but pending handshake
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "cid", "ALLEGRO_CLIENT_SECRET": "csec"}):
        mock_load.return_value = None
        st = get_allegro_token_status()
        assert st["configured"] is True
        assert st["allegro_token_active"] is False
        assert st["reason"] == "oauth_handshake_pending"

    # 3. Active token
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "cid", "ALLEGRO_CLIENT_SECRET": "csec"}):
        with patch("time.time", return_value=1000000000 + 3600):
            mock_load.return_value = {
                "access_token": "active_tok",
                "refresh_token": "ref_tok",
                "created_at": 1000000000,
                "expires_in": 43200,
            }
            st = get_allegro_token_status()
            assert st["configured"] is True
            assert st["allegro_token_active"] is True
            assert st["is_expired"] is False
            assert st["token_age_hours"] == 1.0
            assert st["reason"] == "active"
