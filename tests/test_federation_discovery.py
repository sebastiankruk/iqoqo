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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Tests for ActivityPub Fediverse discovery endpoints (WebFinger, NodeInfo 2.1, Actor JSON-LD)."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest

from app.core import federation_keys
from app.db import db
from app.db.auth import User
from app.db.federation import FederationConsent


@pytest.fixture(autouse=True)
def configure_federation_base_url(app) -> None:
    """Set FEDERATION_BASE_URL to match test host iqoqo.local."""
    app.config["FEDERATION_BASE_URL"] = "http://iqoqo.local"


@pytest.fixture
def custom_keys_dir(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Isolate key storage in temporary test directory."""
    keys_dir = tmp_path / "keys"  # type: ignore[operator]
    monkeypatch.setattr(federation_keys, "_KEYS_DIR", keys_dir)
    yield


@pytest.fixture
def federated_user_data(app) -> dict[str, str]:
    """Create a user with explicit federation consent and return data dict."""
    with app.app_context():
        user = User(
            email="fed_alice@iqoqo.local",
            public_username="alice",
            display_name="Alice Fed",
            bio="Federated bookworm",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

        consent = FederationConsent(
            user_id=user.id,
            federated_profile=True,
            federated_collection=True,
        )
        db.session.add(consent)
        db.session.commit()
        return {
            "id": str(user.id),
            "public_username": "alice",
            "display_name": "Alice Fed",
        }


@pytest.fixture
def non_consenting_user_data(app) -> dict[str, str]:
    """Create a user without federation consent."""
    with app.app_context():
        user = User(
            email="fed_bob@iqoqo.local",
            public_username="bob",
            display_name="Bob Private",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        return {
            "id": str(user.id),
            "public_username": "bob",
        }


class TestWebFingerDiscovery:
    """Test suite for RFC 7033 WebFinger resolution."""

    def test_webfinger_missing_resource(self, client, app):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            resp = client.get("/.well-known/webfinger")
            assert resp.status_code == 400
            data = resp.get_json()
            assert "resource" in data["error"].lower()

    def test_webfinger_federation_disabled(self, client, app, federated_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = False
            username = federated_user_data["public_username"]
            resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@iqoqo.local")
            assert resp.status_code == 404

    def test_webfinger_non_consenting_user(self, client, app, non_consenting_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = non_consenting_user_data["public_username"]
            resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@iqoqo.local")
            assert resp.status_code == 404

    def test_webfinger_consenting_user(self, client, app, federated_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = federated_user_data["public_username"]
            user_id = federated_user_data["id"]
            resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@iqoqo.local")
            assert resp.status_code == 200
            assert resp.mimetype == "application/jrd+json"

            data = resp.get_json()
            assert f"acct:{username}" in data["subject"]
            links = data["links"]
            self_link = next((item for item in links if item.get("rel") == "self"), None)
            assert self_link is not None
            assert self_link["type"] == "application/activity+json"
            assert user_id in self_link["href"]

    def test_webfinger_via_api_prefix(self, client, app, federated_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = federated_user_data["public_username"]
            resp = client.get(f"/api/federation/webfinger?resource=acct:{username}@iqoqo.local")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["subject"].startswith(f"acct:{username}")

    def test_webfinger_domain_mismatch(self, client, app, federated_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = federated_user_data["public_username"]
            resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@remote-instance.com")
            assert resp.status_code == 404
            data = resp.get_json()
            assert "domain mismatch" in data["error"].lower()


class TestNodeInfoDiscovery:
    """Test suite for NodeInfo 2.1 endpoints."""

    def test_wellknown_nodeinfo_disabled(self, client, app):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = False
            resp = client.get("/.well-known/nodeinfo")
            assert resp.status_code == 404

    def test_wellknown_nodeinfo_success(self, client, app):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            resp = client.get("/.well-known/nodeinfo")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "links" in data
            link = data["links"][0]
            assert link["rel"] == "http://nodeinfo.diaspora.software/ns/schema/2.1"
            assert link["href"].endswith("/api/federation/nodeinfo/2.1")

    def test_federation_nodeinfo_2_1(self, client, app):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            resp = client.get("/api/federation/nodeinfo/2.1")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["version"] == "2.1"
            assert data["software"]["name"] == "iqoqo"
            assert "activitypub" in data["protocols"]
            assert "usage" in data
            assert data["usage"]["users"]["total"] >= 0


class TestActorEndpoints:
    """Test suite for ActivityPub Actor JSON-LD representations."""

    def test_actor_by_username_disabled(self, client, app, federated_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = False
            username = federated_user_data["public_username"]
            resp = client.get(f"/api/federation/actor/{username}")
            assert resp.status_code == 404

    def test_actor_by_username_non_consenting(self, client, app, non_consenting_user_data):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = non_consenting_user_data["public_username"]
            resp = client.get(f"/api/federation/actor/{username}")
            assert resp.status_code == 404

    def test_actor_by_username_success(self, client, app, federated_user_data, custom_keys_dir):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            username = federated_user_data["public_username"]
            user_id = federated_user_data["id"]
            resp = client.get(f"/api/federation/actor/{username}")
            assert resp.status_code == 301
            assert resp.headers["Location"].endswith(f"/actor/u/{user_id}")

    def test_actor_by_uuid_success(self, client, app, federated_user_data, custom_keys_dir):
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            user_id = federated_user_data["id"]
            resp = client.get(f"/api/federation/actor/u/{user_id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["type"] == "Person"
            assert user_id in data["id"]

    def test_lookup_unauthenticated_rejected(self, client, app):
        """Verify unauthenticated GET /api/federation/lookup is rejected with 401."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True

        resp = client.get("/api/federation/lookup?handle=@user@remote.domain")
        assert resp.status_code == 401
