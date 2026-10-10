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
import json
from unittest.mock import patch


def test_auth_providers_unconfigured(client):
    """Verify /api/auth/providers returns google: false when unconfigured."""
    with patch("app.api.auth._ensure_google_oauth", return_value=False):
        response = client.get("/api/auth/providers")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"google": False}


def test_auth_providers_configured(client):
    """Verify /api/auth/providers returns google: true when configured."""
    with patch("app.api.auth._ensure_google_oauth", return_value=True):
        response = client.get("/api/auth/providers")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"google": True}


def test_auth_providers_exception_fallback(client):
    """Verify /api/auth/providers gracefully returns google: false on error."""
    with patch("app.api.auth._ensure_google_oauth", side_effect=RuntimeError("Config error")):
        response = client.get("/api/auth/providers")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"google": False}
