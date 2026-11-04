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
    from app.api.auth import _generate_oauth_state

    token_claims = {
        "sub": "apple-user-unique-id-123",
        "email": "appleuser@example.com",
        "email_verified": True,
    }

    state = _generate_oauth_state(callback_url="/collection")

    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.api.auth._verify_apple_id_token", return_value=token_claims),
    ):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = state

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": state,
                "id_token": "valid.apple.jwt",
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
    """Verify Apple callback with mobile_origin=capacitor redirects to ?code= exchange without raw token or HTML."""
    from app.api.auth import _generate_oauth_state

    token_claims = {
        "sub": "apple-mobile-user-456",
        "email": "mobile@example.com",
        "email_verified": True,
    }

    state = _generate_oauth_state(mobile_origin="capacitor")

    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.api.auth._verify_apple_id_token", return_value=token_claims),
    ):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = state

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": state,
                "id_token": "valid.apple.jwt",
            },
        )
        assert response.status_code == 302
        loc = response.headers["Location"]
        assert "/auth-exchange?mobile=1&code=" in loc
        assert "#token=" not in loc
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"


def test_apple_callback_suspended_user_rejected(client, app):
    """Verify that a suspended user (is_active=False) cannot log in via Apple OAuth."""
    from app.api.auth import _generate_oauth_state

    token_claims = {
        "sub": "apple-suspended-user-999",
        "email": "suspended@example.com",
        "email_verified": True,
    }

    with app.app_context():
        user = User(
            email="suspended@example.com",
            apple_id="apple-suspended-user-999",
            is_active=False,
        )
        db.session.add(user)
        db.session.commit()

    state = _generate_oauth_state(mobile_origin="capacitor")

    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.api.auth._verify_apple_id_token", return_value=token_claims),
    ):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = state

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": state,
                "id_token": "valid.apple.jwt",
            },
        )
        assert response.status_code == 302
        assert "login?error=account_suspended" in response.headers["Location"]


def test_apple_callback_tampered_state_rejected(client):
    """Verify that tampered or missing state fails closed."""
    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.api.auth._verify_apple_id_token", return_value={"sub": "123"}),
    ):
        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": "forged-invalid-state",
                "id_token": "valid.apple.jwt",
            },
        )
        assert response.status_code == 302
        assert "login?error=csrf_state_mismatch" in response.headers["Location"]


def test_apple_callback_unverified_email_not_linked(client, app):
    """Verify that unverified Apple email is NOT linked to an existing account."""
    from app.api.auth import _generate_oauth_state

    with app.app_context():
        existing = User(
            email="victim@example.com",
            is_active=True,
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

    token_claims = {
        "sub": "attacker-apple-sub-007",
        "email": "victim@example.com",
        "email_verified": False,  # Not verified!
    }

    state = _generate_oauth_state()

    with (
        patch("app.api.auth._ensure_apple_oauth", return_value=True),
        patch("app.api.auth._verify_apple_id_token", return_value=token_claims),
    ):
        with client.session_transaction() as sess:
            sess["oauth_apple_state"] = state

        response = client.post(
            "/api/auth/callback/apple",
            data={
                "state": state,
                "id_token": "valid.apple.jwt",
            },
        )
        assert response.status_code == 302

        with app.app_context():
            victim = db.session.get(User, existing_id)
            assert victim.apple_id is None
