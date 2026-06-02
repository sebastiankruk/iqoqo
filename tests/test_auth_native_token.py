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
"""Tests for the Bearer-token auth flow used by native Capacitor clients.

In the native app the user cannot rely on httpOnly cookies, so the backend
must accept a ``Authorization: Bearer <jwt>`` header in addition to the
existing session-cookie flow.
"""

import jwt as pyjwt
import pytest


def test_bearer_token_accepted_by_api(client, normal_user_headers, app):
    """A valid Bearer token in the Authorization header must grant access."""
    # normal_user_headers already contains {"Authorization": "Bearer <token>"}
    # which exercises exactly the native auth path.
    res = client.get("/api/profile/", headers=normal_user_headers)
    assert res.status_code == 200, res.data
    data = res.get_json()
    # Profile endpoint wraps payload: {"data": {...}, "success": true}
    payload = data.get("data") or data
    assert payload.get("email") is not None


def test_missing_bearer_token_rejected(client):
    """A request to an authenticated endpoint without credentials returns 401."""
    res = client.get("/api/profile/")
    assert res.status_code == 401


def test_expired_bearer_token_rejected(client, app):
    """An expired JWT must not be accepted."""
    from datetime import UTC, datetime, timedelta

    with app.app_context():
        expired_token = pyjwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000000",
                "jti": "test-jti",
                "email": "ghost@example.com",
                "roles": [],
                "exp": datetime.now(UTC) - timedelta(seconds=1),
                "iat": datetime.now(UTC) - timedelta(days=1),
            },
            app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

    res = client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


def test_invalid_bearer_token_rejected(client):
    """A malformed JWT must not be accepted."""
    res = client.get(
        "/api/profile/",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert res.status_code == 401
