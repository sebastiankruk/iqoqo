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
"""Tests for Federated Library Directory API."""

import pytest

from app.db import db
from app.db.core import Expression, Item, Manifestation, Work
from app.db.federation import FederationInstance, TrustLevel


@pytest.fixture
def directory_seed(app):
    """Seed test data for directory tests."""
    with app.app_context():
        # Add peer instances with various trust levels
        inst_trusted = FederationInstance(
            domain="library.alderaan.example",
            software_name="iqoqo",
            software_version="0.9.1",
            trust_level=TrustLevel.TRUSTED,
        )
        inst_verified = FederationInstance(
            domain="books.naboo.example",
            software_name="iqoqo",
            software_version="0.9.0",
            trust_level=TrustLevel.UNTRUSTED,
        )
        inst_blocked = FederationInstance(
            domain="shady.tatooine.example",
            software_name="suspicious",
            software_version="0.0.1",
            trust_level=TrustLevel.BLOCKED,
        )
        db.session.add_all([inst_trusted, inst_verified, inst_blocked])

        # Add public and private items
        from app.db.auth import User

        user = User(email="dir_user@example.com", display_name="Directory User")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Directory Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, publisher="Galaxy Press")
        db.session.add(manif)
        db.session.flush()

        item_pub = Item(manifestation_id=manif.id, owner_id=user.id, is_hidden=False)
        item_priv = Item(manifestation_id=manif.id, owner_id=user.id, is_hidden=True)
        db.session.add_all([item_pub, item_priv])
        db.session.commit()


def test_get_federation_directory(client, app, directory_seed):
    """Verify directory returns only trusted and verified peers, and counts only public items."""
    res = client.get("/api/federation/directory")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    payload = data["data"]
    assert "local_instance" in payload
    assert payload["local_instance"]["public_items_count"] == 1
    assert payload["total_peers"] == 2

    peer_domains = [p["domain"] for p in payload["peers"]]
    assert "library.alderaan.example" in peer_domains
    assert "books.naboo.example" in peer_domains
    assert "shady.tatooine.example" not in peer_domains


def test_get_federation_directory_disabled(client, app, directory_seed):
    """Verify directory returns 200 with empty peers and federation_enabled=False when disabled."""
    original = app.config.get("FEDERATION_ENABLED")
    app.config["FEDERATION_ENABLED"] = False
    try:
        res = client.get("/api/federation/directory")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        payload = data["data"]
        assert payload["local_instance"]["federation_enabled"] is False
        assert payload["peers"] == []
        assert payload["total_peers"] == 0
    finally:
        app.config["FEDERATION_ENABLED"] = original


def test_get_federation_instance_info(client, app):
    """Verify instance-info returns 200 with local instance metadata."""
    res = client.get("/api/federation/instance-info")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "local_instance" in data["data"]
    assert "federation_enabled" in data["data"]["local_instance"]


def test_get_federation_directory_filters_non_routable_internal_hostnames(client, app, directory_seed):
    """Verify internal Docker, loopback, or non-FQDN hostnames are excluded from directory."""
    with app.app_context():
        # Seed trusted internal instances (e.g. from smoke testing)
        internal_peers = [
            FederationInstance(domain="web:5000", trust_level=TrustLevel.TRUSTED),
            FederationInstance(domain="peer-web:5000", trust_level=TrustLevel.TRUSTED),
            FederationInstance(domain="localhost:5005", trust_level=TrustLevel.TRUSTED),
            FederationInstance(domain="127.0.0.1:8000", trust_level=TrustLevel.TRUSTED),
            FederationInstance(domain="node.local", trust_level=TrustLevel.TRUSTED),
        ]
        db.session.add_all(internal_peers)
        db.session.commit()

    res = client.get("/api/federation/directory")
    assert res.status_code == 200
    payload = res.get_json()["data"]
    peer_domains = [p["domain"] for p in payload["peers"]]

    # Public FQDNs must be present
    assert "library.alderaan.example" in peer_domains
    assert "books.naboo.example" in peer_domains

    # Non-routable internal hostnames must NOT be exposed
    assert "web:5000" not in peer_domains
    assert "peer-web:5000" not in peer_domains
    assert "localhost:5005" not in peer_domains
    assert "127.0.0.1:8000" not in peer_domains
    assert "node.local" not in peer_domains
