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
"""Tests for the Google OAuth mobile redirect flow.

When the Capacitor native app initiates Google login, the backend must use
a dedicated mobile callback URL (``/callback/google/mobile``) so that the
callback always redirects to the ``iqoqo://`` deep-link scheme.

This avoids relying on authlib's ``state`` parameter (which gets overwritten
by authlib's own CSRF token) or Flask ``session`` (which is lost when the
WebView opens Google's login page in the system browser).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.db.models import Role, User, db


@pytest.fixture(autouse=True)
def setup_roles(app):
    """Ensure the default 'user' role exists in the test DB."""
    if not Role.query.filter_by(name="user").first():
        db.session.add(Role(name="user"))
        db.session.commit()


class TestGoogleLoginMobileOrigin:
    """Verify that /login/google routes to the correct callback URL."""

    def test_web_login_uses_standard_callback(self, client):
        """Without mobile_origin, redirect_uri must point to /callback/google."""
        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect.return_value = MagicMock(status_code=302)

            client.get("/api/auth/login/google")

            mock_oauth.google.authorize_redirect.assert_called_once()
            redirect_uri = mock_oauth.google.authorize_redirect.call_args[0][0]
            assert redirect_uri.endswith("/api/auth/callback/google")
            assert "mobile" not in redirect_uri

    def test_mobile_login_uses_mobile_callback(self, client):
        """With mobile_origin=capacitor, redirect_uri must point to /callback/google/mobile."""
        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect.return_value = MagicMock(status_code=302)

            client.get("/api/auth/login/google?mobile_origin=capacitor")

            mock_oauth.google.authorize_redirect.assert_called_once()
            redirect_uri = mock_oauth.google.authorize_redirect.call_args[0][0]
            assert redirect_uri.endswith("/api/auth/callback/google/mobile")

    def test_mobile_login_ignores_unknown_origin(self, client):
        """An unrecognized mobile_origin value should use the standard callback."""
        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect.return_value = MagicMock(status_code=302)

            client.get("/api/auth/login/google?mobile_origin=flutter")

            redirect_uri = mock_oauth.google.authorize_redirect.call_args[0][0]
            assert redirect_uri.endswith("/api/auth/callback/google")
            assert "mobile" not in redirect_uri


class TestGoogleCallbackMobile:
    """Verify the mobile callback always redirects to iqoqo:// deep link."""

    def _mock_oauth_token_exchange(self, email="test@google.com", name="Test User", sub="google-123", picture=None):
        """Create a mock for the OAuth token exchange that returns user info."""
        mock_token = {"access_token": "fake-access-token"}
        mock_user_info = {
            "email": email,
            "name": name,
            "sub": sub,
            "picture": picture,
        }
        return mock_token, mock_user_info

    def test_mobile_callback_redirects_to_deep_link(self, client, app):
        """The /callback/google/mobile route must serve the redirect HTML page."""
        mock_token, mock_user_info = self._mock_oauth_token_exchange()

        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = mock_token
            mock_oauth.google.parse_id_token.return_value = mock_user_info

            response = client.get("/api/auth/callback/google/mobile")

            assert response.status_code == 200
            html = response.data.decode("utf-8")
            assert "iqoqo://auth-exchange?token=" in html

    def test_web_callback_redirects_to_frontend(self, client, app):
        """The /callback/google (web) route must redirect to the frontend URL."""
        mock_token, mock_user_info = self._mock_oauth_token_exchange()

        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = mock_token
            mock_oauth.google.parse_id_token.return_value = mock_user_info

            response = client.get("/api/auth/callback/google")

            assert response.status_code == 302
            location = response.headers.get("Location", "")
            assert "/auth-exchange?token=" in location
            assert not location.startswith("iqoqo://")

    def test_mobile_callback_creates_new_user(self, client, app):
        """The mobile callback must create a new user if one does not exist."""
        mock_token, mock_user_info = self._mock_oauth_token_exchange(
            email="new_mobile@google.com",
            name="New Mobile User",
            sub="google-new-mobile",
        )

        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = mock_token
            mock_oauth.google.parse_id_token.return_value = mock_user_info

            response = client.get("/api/auth/callback/google/mobile")

            assert response.status_code == 200
            # Verify user was created
            with app.app_context():
                user = db.session.execute(db.select(User).filter_by(email="new_mobile@google.com")).scalar_one_or_none()
                assert user is not None
                assert user.display_name == "New Mobile User"
                assert user.google_id == "google-new-mobile"

    def test_mobile_callback_token_is_valid_jwt(self, client, app):
        """The token in the deep-link redirect must be a valid JWT."""
        import re

        import jwt as pyjwt

        mock_token, mock_user_info = self._mock_oauth_token_exchange()

        with patch("app.api.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = mock_token
            mock_oauth.google.parse_id_token.return_value = mock_user_info

            response = client.get("/api/auth/callback/google/mobile")

            html = response.data.decode("utf-8")
            match = re.search(r"token=([a-zA-Z0-9_\-\.]+)", html)
            assert match is not None
            token_value = match.group(1)

            # Decode and verify the token
            with app.app_context():
                payload = pyjwt.decode(token_value, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
                assert payload["email"] == "test@google.com"
                assert "sub" in payload
                assert "jti" in payload
