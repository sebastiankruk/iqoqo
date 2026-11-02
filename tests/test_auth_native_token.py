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
"""Tests for native bearer tokens and mobile CORS permissions."""

from app.api.auth import generate_internal_jwt
from app.db.models import Role, User, db


def test_native_bearer_token_authenticates_requests(client, app):
    """Verify generated internal JWT bearer token authenticates user requests."""
    with app.app_context():
        user = User(email="bearer-test@example.com", is_active=True, password_hash="dummy")
        role = db.session.execute(db.select(Role).filter_by(name="user")).scalar_one_or_none()
        if role:
            user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        token = generate_internal_jwt(user)

    response = client.get(
        "/api/auth/tokens",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert "items" in data


def test_native_mobile_cors_preflight():
    """Verify OPTIONS preflight request from capacitor://localhost returns allowed CORS headers."""
    from app import create_app

    cors_app = create_app(
        config_override={
            "TESTING": True,
            "CORS_ENABLED": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
            "RATELIMIT_ENABLED": False,
        }
    )
    with cors_app.test_client() as client:
        response = client.open(
            "/api/auth/tokens",
            method="OPTIONS",
            headers={
                "Origin": "capacitor://localhost",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "capacitor://localhost"
