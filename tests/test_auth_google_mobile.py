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
"""Tests for Google OAuth mobile pass-through."""

from unittest.mock import MagicMock, patch

from app.db.models import User, db


def test_google_login_captures_mobile_origin(client):
    """Verify google_login stores mobile_origin=capacitor in session."""
    with patch("app.api.auth._ensure_google_oauth", return_value=True), patch("app.api.auth.oauth.google") as mock_google:
        mock_google.authorize_redirect.return_value = ("redirect-response", 302)
        response = client.get("/api/auth/login/google?mobile_origin=capacitor")
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("oauth_mobile_origin") == "capacitor"


def test_google_callback_mobile_redirect(client, app):
    """Verify Google callback with mobile_origin=capacitor redirects to #token hash."""
    user_info = {
        "sub": "google-mobile-user-789",
        "email": "googlemobile@example.com",
        "name": "Grace Hopper",
        "email_verified": True,
    }

    with patch("app.api.auth._ensure_google_oauth", return_value=True), patch("app.api.auth.oauth.google") as mock_google:
        mock_google.authorize_access_token.return_value = {"access_token": "fake-access-token"}
        mock_google.parse_id_token.return_value = user_info

        with client.session_transaction() as sess:
            sess["oauth_mobile_origin"] = "capacitor"

        response = client.get("/api/auth/callback/google")
        assert response.status_code == 302
        loc = response.headers["Location"]
        assert "/auth-exchange?mobile=1#token=" in loc
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"

        with app.app_context():
            user = db.session.execute(db.select(User).filter_by(google_id="google-mobile-user-789")).scalar_one_or_none()
            assert user is not None
            assert user.email == "googlemobile@example.com"
