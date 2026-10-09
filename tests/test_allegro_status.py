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
import time
from unittest.mock import patch

from app.utils.allegro import get_allegro_token_status


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_not_configured(mock_load):
    """Verify not_configured state when credentials are unset."""
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "", "ALLEGRO_CLIENT_SECRET": ""}, clear=True):
        with patch("app.db.models.InstanceSettings.get_value", return_value=None):
            st = get_allegro_token_status()
            assert st["configured"] is False
            assert st["allegro_token_active"] is False
            assert st["reason"] == "not_configured"
            assert st["token_age_hours"] is None


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_handshake_pending(mock_load):
    """Verify handshake_pending state when credentials exist but no token stored."""
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_sec"}):
        mock_load.return_value = None
        st = get_allegro_token_status()
        assert st["configured"] is True
        assert st["allegro_token_active"] is False
        assert st["reason"] == "handshake_pending"
        assert st["token_age_hours"] is None


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_active(mock_load):
    """Verify active state with fresh access token."""
    now = 1700000000.0
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_sec"}):
        with patch("time.time", return_value=now + 3600):
            mock_load.return_value = {
                "access_token": "active_tok",
                "refresh_token": "ref_tok",
                "created_at": now,
                "expires_in": 43200,
            }
            st = get_allegro_token_status()
            assert st["configured"] is True
            assert st["allegro_token_active"] is True
            assert st["is_expired"] is False
            assert st["has_refresh_token"] is True
            assert st["token_age_hours"] == 1.0
            assert st["reason"] == "active"


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_expired(mock_load):
    """Verify expired state when token is expired and refresh token is absent."""
    now = 1700000000.0
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_sec"}):
        with patch("time.time", return_value=now + 50000):
            mock_load.return_value = {
                "access_token": "old_tok",
                "refresh_token": "",
                "created_at": now,
                "expires_in": 43200,
            }
            st = get_allegro_token_status()
            assert st["configured"] is True
            assert st["allegro_token_active"] is False
            assert st["is_expired"] is True
            assert st["has_refresh_token"] is False
            assert st["reason"] == "expired"


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_probe_error_settings(mock_load):
    """Verify probe_error state when InstanceSettings raises an exception."""
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "", "ALLEGRO_CLIENT_SECRET": ""}, clear=True):
        with patch("app.db.models.InstanceSettings.get_value", side_effect=RuntimeError("DB disconnected")):
            st = get_allegro_token_status()
            assert st["configured"] is False
            assert st["allegro_token_active"] is False
            assert st["reason"] == "probe_error"
            assert "DB disconnected" in st.get("error", "")


@patch("app.utils.allegro.load_allegro_token")
def test_allegro_status_probe_error_token_load(mock_load):
    """Verify probe_error state when load_allegro_token raises an exception."""
    with patch.dict("os.environ", {"ALLEGRO_CLIENT_ID": "test_id", "ALLEGRO_CLIENT_SECRET": "test_sec"}):
        mock_load.side_effect = RuntimeError("Decryption failed")
        st = get_allegro_token_status()
        assert st["configured"] is True
        assert st["allegro_token_active"] is False
        assert st["reason"] == "probe_error"
        assert "Decryption failed" in st.get("error", "")
