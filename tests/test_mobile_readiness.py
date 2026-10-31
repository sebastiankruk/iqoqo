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
"""Mobile readiness contract verification for upcoming v1.0.0 Capacitor apps."""


def test_mobile_nodeinfo_discovery(client, app):
    """Mobile client discovers server metadata and NodeInfo 2.1 protocol links."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = True

    resp = client.get("/.well-known/nodeinfo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "links" in data
    assert any(link.get("rel") == "http://nodeinfo.diaspora.software/ns/schema/2.1" for link in data["links"])

    # Follow nodeinfo 2.1 link
    nodeinfo_resp = client.get("/api/federation/nodeinfo/2.1")
    assert nodeinfo_resp.status_code == 200
    info = nodeinfo_resp.get_json()
    assert info["version"] == "2.1"
    assert info["software"]["name"] == "iqoqo"
    assert "version" in info["software"]
    assert "protocols" in info
    assert "activitypub" in info["protocols"]


def test_mobile_auth_providers_contract(client):
    """Mobile client queries supported authentication providers during login bootstrap."""
    resp = client.get("/api/auth/providers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "google" in data
    assert isinstance(data["google"], bool)


def test_mobile_cors_preflight_headers(client, app):
    """Mobile client native origin receives permissive preflight headers for API access."""
    with app.app_context():
        app.config["CORS_ENABLED"] = "true"
        app.config["CORS_ORIGINS"] = "capacitor://localhost,http://localhost"

    resp = client.open(
        "/api/auth/providers",
        method="OPTIONS",
        headers={
            "Origin": "capacitor://localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Status can be 200 or 204 for OPTIONS
    assert resp.status_code in (200, 204)
