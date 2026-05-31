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
"""Tests for the Sign in with Apple OAuth backend routes.

Because we cannot perform a real Apple OAuth round-trip in CI, these tests
verify route existence, guard behaviour (disabled when unconfigured), and
the apple_id column is present on the User model.
"""
import pytest


def test_apple_login_route_unavailable_when_unconfigured(client, app):
    """When APPLE_CLIENT_ID is not set, /api/auth/login/apple returns 503."""
    with app.app_context():
        app.config["APPLE_CLIENT_ID"] = None

    res = client.get("/api/auth/login/apple")
    assert res.status_code == 503
    data = res.get_json()
    assert "not configured" in data.get("error", "").lower()


def test_apple_callback_route_unavailable_when_unconfigured(client, app):
    """When APPLE_CLIENT_ID is not set, /api/auth/callback/apple returns 503."""
    with app.app_context():
        app.config["APPLE_CLIENT_ID"] = None

    res = client.post("/api/auth/callback/apple")
    assert res.status_code == 503


def test_user_model_has_apple_id_column(app):
    """The User model must expose an apple_id attribute for Sign in with Apple."""
    from app.db.auth import User

    with app.app_context():
        assert hasattr(User, "apple_id"), "User model is missing apple_id column"
        col = User.__table__.columns.get("apple_id")
        assert col is not None, "apple_id is not a mapped DB column"
        assert col.nullable is True, "apple_id must be nullable"
        assert col.unique is True, "apple_id must be unique"
