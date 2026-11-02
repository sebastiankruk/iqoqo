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
"""Tests for Sign in with Apple OAuth endpoints."""

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import jwt as pyjwt
import pytest

from app.db.models import User, db


def test_apple_login_unconfigured(client):
    """Verify apple_login redirects to error when unconfigured."""
    with patch("app.api.auth._ensure_apple_oauth", return_value=False):
        response = client.get("/api/auth/login/apple")
        assert response.status_code == 302
        assert "login?error=apple_oauth_not_configured" in response.headers["Location"]


def test_apple_login_configured_redirect(client):
    """Verify apple_login redirects to Apple OAuth authorize endpoint."""
    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.core.config_service.ConfigService.get", return_value="com.iqoqo.app"),
    ):
        response = client.get("/api/auth/login/apple?callbackUrl=/collection")
        assert response.status_code == 302
        loc = response.headers["Location"]
        assert loc.startswith("https://appleid.apple.com/auth/authorize")

        parsed = urlparse(loc)
        qs = parse_qs(parsed.query)
        assert qs["client_id"] == ["com.iqoqo.app"]
        assert qs["response_type"] == ["code id_token"]
        assert qs["response_mode"] == ["form_post"]
        assert qs["scope"] == ["name email"]
        assert "state" in qs


def test_apple_callback_web_success(client, app):
    """Verify Apple callback creates user and redirects to web /api/auth-exchange."""
    token_claims = {
        "sub": "apple-user-unique-id-123",
        "email": "appleuser@example.com",
        "email_verified": True,
    }
    fake_id_token = pyjwt.encode(token_claims, "secret-key-at-least-32-bytes-long!", algorithm="HS256")

    with patch("app.api.auth._ensure_apple_oauth", return_value=True):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = "csrf-state-abc"

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": "csrf-state-abc",
                "id_token": fake_id_token,
                "user": json.dumps({"name": {"firstName": "Ada", "lastName": "Lovelace"}}),
            },
        )
        assert response.status_code == 302
        loc = response.headers["Location"]
        assert "/api/auth-exchange?code=" in loc

        with app.app_context():
            user = db.session.execute(db.select(User).filter_by(apple_id="apple-user-unique-id-123")).scalar_one_or_none()
            assert user is not None
            assert user.email == "appleuser@example.com"
            assert user.display_name == "Ada Lovelace"


def test_apple_callback_mobile_capacitor_redirect(client, app):
    """Verify Apple callback with mobile_origin=capacitor redirects to #token hash without HTML."""
    token_claims = {
        "sub": "apple-mobile-user-456",
        "email": "mobile@example.com",
        "email_verified": True,
    }
    fake_id_token = pyjwt.encode(token_claims, "secret-key-at-least-32-bytes-long!", algorithm="HS256")

    with patch("app.api.auth._ensure_apple_oauth", return_value=True):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = "csrf-state-xyz"
            sess["oauth_mobile_origin"] = "capacitor"

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": "csrf-state-xyz",
                "id_token": fake_id_token,
            },
        )
        assert response.status_code == 302
        loc = response.headers["Location"]
        assert "/auth-exchange?mobile=1#token=" in loc
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"
