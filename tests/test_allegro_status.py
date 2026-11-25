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


def test_allegro_invalid_grant_persists_failure_without_jwt_leak(app, caplog):
    """400 invalid_grant marks token refresh_failed without leaking JWT error_description."""
    import logging
    from unittest.mock import MagicMock

    from app.core.cache import cache
    from app.db.models import InstanceSettings
    from app.utils.allegro import _refresh_user_token, get_allegro_token, has_allegro_user_token, save_allegro_token

    jwt_secret = "eyJhbGciOiJIUzI1NiJ9.supersecretjwtpayload.sig"
    with app.app_context():
        InstanceSettings.set_value("ALLEGRO_CLIENT_ID", "cid_123")
        InstanceSettings.set_value("ALLEGRO_CLIENT_SECRET", "csec_456")
        old_tokens = {
            "access_token": "old_acc",
            "refresh_token": jwt_secret,
            "created_at": time.time() - 60000,
            "expires_in": 43200,
        }
        save_allegro_token(old_tokens)

        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": "invalid_grant",
            "error_description": f"Invalid refresh token: {jwt_secret}",
        }

        with caplog.at_level(logging.WARNING, logger="app.utils.allegro"):
            with patch("app.utils.allegro.requests.post", return_value=mock_resp):
                refreshed = _refresh_user_token(old_tokens, "cid_123", "csec_456", {"User-Agent": "test"})

        assert refreshed is None
        assert jwt_secret not in caplog.text
        assert InstanceSettings.get_value("ALLEGRO_CLIENT_ID") == "cid_123"
        assert InstanceSettings.get_value("ALLEGRO_CLIENT_SECRET") == "csec_456"

        stored = InstanceSettings.get_value("ALLEGRO_TOKEN_DATA")
        assert stored["refresh_failed"] is True
        assert stored["refresh_error"] == "invalid_grant"
        assert isinstance(stored["refresh_failed_at"], float)
        assert jwt_secret not in str(stored.get("refresh_error"))

        assert has_allegro_user_token() is False
        st = get_allegro_token_status()
        assert st["allegro_token_active"] is False
        assert st["reason"] == "reauth_required"
        assert st["refresh_error"] == "invalid_grant"

        # Subsequent get_allegro_token() MUST NOT repeat refresh_token POST
        cc_resp = MagicMock()
        cc_resp.ok = True
        cc_resp.status_code = 200
        cc_resp.json.return_value = {"access_token": "cc_tok"}
        with patch("app.utils.allegro.requests.post", return_value=cc_resp) as mock_post:
            tok = get_allegro_token()
        assert tok == "cc_tok"
        assert mock_post.call_count == 1
        assert mock_post.call_args.kwargs["data"]["grant_type"] == "client_credentials"

        # Re-authorizing via save_allegro_token clears failure flags
        save_allegro_token({"access_token": "fresh_acc", "refresh_token": "fresh_ref", "expires_in": 43200})
        cleared = cache.get("allegro_token_data")
        assert "refresh_failed" not in cleared
        assert "refresh_error" not in cleared
        assert has_allegro_user_token() is True
        assert get_allegro_token_status()["reason"] == "active"


def test_allegro_transient_503_does_not_poison_token_and_probe_remote(app):
    """Transient 503/timeout leaves token retryable; probe_remote=True triggers refresh."""
    from unittest.mock import MagicMock

    from app.db.models import InstanceSettings
    from app.utils.allegro import _refresh_user_token, load_allegro_token, save_allegro_token

    with app.app_context():
        InstanceSettings.set_value("ALLEGRO_CLIENT_ID", "cid_123")
        InstanceSettings.set_value("ALLEGRO_CLIENT_SECRET", "csec_456")
        expired_tokens = {
            "access_token": "exp_acc",
            "refresh_token": "ref_tok",
            "created_at": time.time() - 60000,
            "expires_in": 43200,
        }
        save_allegro_token(expired_tokens)

        resp_503 = MagicMock()
        resp_503.ok = False
        resp_503.status_code = 503
        resp_503.raise_for_status.side_effect = RuntimeError("503 Service Unavailable")
        with patch("app.utils.allegro.requests.post", return_value=resp_503):
            try:
                _refresh_user_token(expired_tokens, "cid_123", "csec_456", {"User-Agent": "test"})
            except RuntimeError:
                pass
        assert not (load_allegro_token() or {}).get("refresh_failed")

        # probe_remote=True attempts refresh and flips to reauth_required on invalid_grant
        resp_400 = MagicMock()
        resp_400.ok = False
        resp_400.status_code = 400
        resp_400.json.return_value = {"error": "invalid_grant"}
        with patch("app.utils.allegro.requests.post", return_value=resp_400):
            st = get_allegro_token_status(probe_remote=True)
        assert st["allegro_token_active"] is False
        assert st["reason"] == "reauth_required"


def test_allegro_403_logs_warning_with_auth_mode_without_secret(caplog):
    """fetch_allegro_candidates logs WARNING with endpoint, status, and auth_mode on 403."""
    import logging
    from unittest.mock import MagicMock

    from app.utils.allegro import fetch_allegro_candidates

    secret_token = "super_secret_bearer_xyz"
    resp_403 = MagicMock()
    resp_403.status_code = 403

    with caplog.at_level(logging.WARNING, logger="app.utils.allegro"):
        with (
            patch("app.utils.allegro._get_allegro_token_with_mode", return_value=(secret_token, "client_credentials")),
            patch("app.utils.allegro.requests.get", return_value=resp_403) as mock_get,
        ):
            results = fetch_allegro_candidates("9788301000003")

    assert results == []
    # client_credentials MUST NOT call /offers/listing
    assert mock_get.call_count == 1
    assert "/sale/products" in mock_get.call_args.args[0]
    assert "403" in caplog.text
    assert "client_credentials" in caplog.text
    assert secret_token not in caplog.text


def test_load_allegro_token_prefers_db_over_stale_simplecache(app):
    """Multi-worker SimpleCache stale refresh_failed never overrides fresh InstanceSettings token."""
    from app.core.cache import cache
    from app.db.models import InstanceSettings
    from app.utils.allegro import load_allegro_token

    with app.app_context():
        cache.set(
            "allegro_token_data",
            {"access_token": "stale_tok", "refresh_failed": True, "refresh_error": "invalid_grant"},
            timeout=86400,
        )
        InstanceSettings.set_value(
            "ALLEGRO_TOKEN_DATA",
            {"access_token": "fresh_db_tok", "refresh_token": "fresh_ref", "created_at": time.time()},
        )
        loaded = load_allegro_token()
        assert loaded is not None
        assert loaded["access_token"] == "fresh_db_tok"
        assert not loaded.get("refresh_failed")
