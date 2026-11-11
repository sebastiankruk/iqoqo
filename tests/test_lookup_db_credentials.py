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
"""Tests for database-backed credential resolution, sanitization, and status reporting."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config_service import ConfigService, sanitize_credential_string
from app.db.models import InstanceSettings, db
from app.utils.bgg import get_bgg_headers
from app.utils.discogs import _get_discogs_auth_header, get_discogs_status
from app.utils.igdb import _get_igdb_client_id, _get_igdb_client_secret
from app.utils.llm_covers import generate_cover_cloud, generate_cover_gemini, generate_cover_local
from app.utils.tmdb import fetch_video_metadata
from app.utils.upc import fetch_upc_metadata, fetch_upcdatabase_org
from app.utils.vision import _extract_via_gemini


def test_sanitize_credential_string():
    """Verify that outer whitespace and surrounding single or double quotes are stripped."""
    assert sanitize_credential_string('  "my-secret-key"  ') == "my-secret-key"
    assert sanitize_credential_string("  'my-secret-key'  ") == "my-secret-key"
    assert sanitize_credential_string('"nested"quote"') == 'nested"quote'
    assert sanitize_credential_string("clean_token") == "clean_token"
    assert sanitize_credential_string(None) is None
    assert sanitize_credential_string(12345) == 12345


def test_config_service_strips_quotes_from_db(app):
    """Verify ConfigService.get returns sanitized value from InstanceSettings."""
    with app.app_context():
        InstanceSettings.set_value("TEST_QUOTED_KEY", '"quoted_db_value"')
        assert ConfigService.get("TEST_QUOTED_KEY") == "quoted_db_value"


def test_config_service_not_shadowed_by_none_in_app_config(app):
    """Verify None value on current_app.config does not shadow os.environ or default."""
    with app.app_context():
        app.config["SHADOWED_KEY"] = None
        with patch.dict(os.environ, {"SHADOWED_KEY": "env_fallback_value"}):
            assert ConfigService.get("SHADOWED_KEY") == "env_fallback_value"


def test_instance_settings_get_configured_keys(app):
    """Verify InstanceSettings.get_configured_keys lists only keys with non-empty values."""
    with app.app_context():
        InstanceSettings.set_value("TEST_CONF_KEY_1", "val1")
        InstanceSettings.set_value("TEST_CONF_KEY_2", "val2")
        keys = InstanceSettings.get_configured_keys()
        assert "TEST_CONF_KEY_1" in keys
        assert "TEST_CONF_KEY_2" in keys


def test_discogs_auth_header_db_resolution(app):
    """Verify Discogs auth resolves from InstanceSettings when os.environ is cleared."""
    with app.app_context():
        with patch.dict(os.environ, {"DISCOGS_CONSUMER_KEY": "", "DISCOGS_CONSUMER_SECRET": "", "DISCOGS_USER_TOKEN": ""}, clear=True):
            # Test user token
            InstanceSettings.set_value("DISCOGS_USER_TOKEN", '"test-discogs-user-token"')
            InstanceSettings.set_value("DISCOGS_CONSUMER_KEY", None)
            InstanceSettings.set_value("DISCOGS_CONSUMER_SECRET", None)

            header = _get_discogs_auth_header()
            assert header == "Discogs token=test-discogs-user-token"

            status = get_discogs_status()
            assert status["configured"] is True
            assert status["auth_mode"] == "user_token"
            assert status["source"] == "db"

            # Test consumer key/secret
            InstanceSettings.set_value("DISCOGS_USER_TOKEN", None)
            InstanceSettings.set_value("DISCOGS_CONSUMER_KEY", "'my_consumer_key'")
            InstanceSettings.set_value("DISCOGS_CONSUMER_SECRET", '"my_consumer_secret"')

            header = _get_discogs_auth_header()
            assert header == "Discogs key=my_consumer_key, secret=my_consumer_secret"

            status = get_discogs_status()
            assert status["configured"] is True
            assert status["auth_mode"] == "consumer_oauth"
            assert status["source"] == "db"


def test_tmdb_db_resolution(app):
    """Verify TMDB resolves API key and read access token from InstanceSettings."""
    with app.app_context():
        with patch.dict(os.environ, {"TMDB_API_KEY": "", "TMDB_API_READ_ACCESS_TOKEN": ""}, clear=True):
            InstanceSettings.set_value("TMDB_API_READ_ACCESS_TOKEN", '"tmdb-bearer-token"')
            with patch("app.utils.tmdb.requests.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"results": []}
                mock_get.return_value = mock_resp

                fetch_video_metadata("Inception")
                assert mock_get.called
                _, kwargs = mock_get.call_args
                assert kwargs["headers"]["Authorization"] == "Bearer tmdb-bearer-token"


def test_upc_db_resolution(app):
    """Verify UPC lookup helpers resolve database keys from InstanceSettings."""
    with app.app_context():
        with patch.dict(os.environ, {"UPC_DATABASE_ORG_KEY": "", "UPC_ITEM_DB_KEY": ""}, clear=True):
            InstanceSettings.set_value("UPC_DATABASE_ORG_KEY", '"upc-org-secret-key"')
            with patch("app.utils.upc.requests.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"valid": "false"}
                mock_get.return_value = mock_resp

                fetch_upcdatabase_org("012345678901")
                assert mock_get.called
                assert "apikey=upc-org-secret-key" in mock_get.call_args[0][0]

            InstanceSettings.set_value("UPC_ITEM_DB_KEY", "'upc-item-secret-key'")
            with patch("app.utils.upc.requests.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"items": []}
                mock_get.return_value = mock_resp

                fetch_upc_metadata("012345678901")
                assert mock_get.called
                _, kwargs = mock_get.call_args
                assert kwargs["headers"]["user_key"] == "upc-item-secret-key"


def test_igdb_db_client_id_resolution(app):
    """Verify IGDB client ID / secret resolve from InstanceSettings."""
    with app.app_context():
        with patch.dict(
            os.environ, {"IGDB_CLIENT_ID": "", "TWITCH_CLIENT_ID": "", "IGDB_CLIENT_SECRET": "", "TWITCH_CLIENT_SECRET": ""}, clear=True
        ):
            InstanceSettings.set_value("IGDB_CLIENT_ID", '"db-igdb-client-id"')
            InstanceSettings.set_value("IGDB_CLIENT_SECRET", '"db-igdb-client-secret"')

            assert _get_igdb_client_id() == "db-igdb-client-id"
            assert _get_igdb_client_secret() == "db-igdb-client-secret"


def test_bgg_db_token_resolution(app):
    """Verify BoardGameGeek headers resolve BGG_API_TOKEN from InstanceSettings."""
    with app.app_context():
        with patch.dict(os.environ, {"BGG_API_TOKEN": ""}, clear=True):
            InstanceSettings.set_value("BGG_API_TOKEN", '"db-bgg-token"')
            headers = get_bgg_headers()
            assert headers["Authorization"] == "Bearer db-bgg-token"


def test_vision_and_llm_covers_db_resolution(app):
    """Verify Gemini and OpenAI API keys resolve from InstanceSettings."""
    with app.app_context():
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "LOCAL_SD_URL": ""}, clear=True):
            InstanceSettings.set_value("GEMINI_API_KEY", '"db-gemini-key"')
            InstanceSettings.set_value("OPENAI_API_KEY", '"db-openai-key"')
            InstanceSettings.set_value("LOCAL_SD_URL", "http://127.0.0.1:7860")

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value.text = '{"Title": "Sample Title"}'
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True

            with (
                patch("app.utils.vision.db.session.get", return_value=mock_user),
                patch("app.utils.vision.Config.ALLOW_LLM", True),
                patch("google.genai.Client", return_value=mock_client) as mock_client_cls,
            ):
                res = _extract_via_gemini(b"fake-bytes", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")
                assert res is not None
                assert res["Title"] == "Sample Title"
                mock_client_cls.assert_called_with(api_key="db-gemini-key")

            with (
                patch("app.utils.llm_covers.OpenAI") as mock_openai_cls,
                patch("app.utils.llm_covers.requests.get") as mock_http_get,
                patch("app.utils.llm_covers.save_image", return_value=(b"fake-bytes", "llm_openai")),
            ):
                mock_client = MagicMock()
                mock_openai_cls.return_value = mock_client
                mock_data = MagicMock()
                mock_data.url = "http://example.com/image.png"
                mock_client.images.generate.return_value.data = [mock_data]
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.content = b"fake-bytes"
                mock_http_get.return_value = mock_resp

                res = generate_cover_cloud("item-1", "Title", "Author", "user-id", return_bytes=True)
                assert res is not None
                mock_openai_cls.assert_called_with(api_key="db-openai-key")

            import base64

            b64_payload = base64.b64encode(b"fake_image_content").decode("ascii")
            with (
                patch("app.utils.llm_covers.requests.post") as mock_post,
                patch("app.utils.llm_covers.save_image", return_value=b"fake-bytes"),
                patch("app.utils.images.add_text_overlay_bytes", return_value=b"overlayed-bytes"),
            ):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"images": [b64_payload]}
                mock_post.return_value = mock_resp

                res = generate_cover_local("item-1", "Title", "Author", "user-id", return_bytes=True)
                assert res is not None
                assert mock_post.called
                assert mock_post.call_args[0][0].startswith("http://127.0.0.1:7860")


def test_system_status_endpoint_reports_db_source(client, normal_user_headers, app):
    """Verify GET /api/system/status reports source='db' when credentials live in InstanceSettings."""
    with app.app_context():
        with patch.dict(
            os.environ,
            {
                "BGG_API_TOKEN": "",
                "DISCOGS_USER_TOKEN": "",
                "DISCOGS_CONSUMER_KEY": "",
                "DISCOGS_CONSUMER_SECRET": "",
                "TMDB_API_KEY": "",
                "TMDB_API_READ_ACCESS_TOKEN": "",
                "GOOGLE_BOOKS_API_KEY": "",
                "UPC_ITEM_DB_KEY": "",
                "UPC_DATABASE_ORG_KEY": "",
                "REBRICKABLE_API_KEY": "",
            },
            clear=True,
        ):
            InstanceSettings.set_value("BGG_API_TOKEN", "bgg-token-val")
            InstanceSettings.set_value("DISCOGS_USER_TOKEN", "discogs-token-val")
            InstanceSettings.set_value("TMDB_API_KEY", "tmdb-key-val")
            InstanceSettings.set_value("GOOGLE_BOOKS_API_KEY", "gb-key-val")
            InstanceSettings.set_value("UPC_ITEM_DB_KEY", "upc-key-val")
            InstanceSettings.set_value("REBRICKABLE_API_KEY", "reb-key-val")

            response = client.get("/api/system/status", headers=normal_user_headers)
            assert response.status_code == 200
            data = response.json
            assert data["success"] is True

            payload = data["data"]
            assert payload["bgg"]["source"] == "db"
            assert payload["bgg"]["configured"] is True

            assert payload["rebrickable"]["source"] == "db"
            assert payload["rebrickable"]["configured"] is True

            assert payload["discogs"]["source"] == "db"
            assert payload["discogs"]["configured"] is True

            assert payload["tmdb"]["source"] == "db"
            assert payload["tmdb"]["configured"] is True

            assert payload["google_books"]["source"] == "db"
            assert payload["google_books"]["configured"] is True

            assert payload["upc"]["source"] == "db"
            assert payload["upc"]["configured"] is True
