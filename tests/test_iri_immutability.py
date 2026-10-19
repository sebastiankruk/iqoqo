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
"""Unit and integration tests verifying Actor IRI immutability and WebFinger resolution across username updates."""

from __future__ import annotations

import uuid

import pytest

from app.core.iri import canonical_actor_iri, legacy_actor_iri
from app.db import db
from app.db.auth import User
from app.db.federation import FederationConsent


@pytest.fixture
def test_user(app):
    """Create a persistent user with a known username for IRI tests."""
    with app.app_context():
        user = User(
            email="fed_test_user@iqoqo.local",
            display_name="Federation Tester",
            public_username="fedtester_v1",
            visibility="public",
            bio="Federation tester bio",
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        consent = FederationConsent(
            user_id=user.id,
            federated_profile=True,
            federated_collection=True,
        )
        db.session.add(consent)
        db.session.commit()
        user_id = user.id
        db.session.remove()

    yield user_id

    with app.app_context():
        u = db.session.get(User, user_id)
        if u:
            db.session.delete(u)
            db.session.commit()
            db.session.remove()


def test_canonical_actor_iri_generation(app):
    """Verify canonical actor IRI formats properly with user UUID."""
    user_uuid = uuid.uuid4()
    iri = canonical_actor_iri(user_uuid, base_url="https://test.iqoqo.cc")
    assert iri == f"https://test.iqoqo.cc/api/federation/actor/u/{user_uuid}"


def test_canonical_actor_iri_invalid_inputs():
    """Verify ValueError is raised on empty identifiers."""
    with pytest.raises(ValueError, match="non-empty user identifier"):
        canonical_actor_iri(None)
    with pytest.raises(ValueError, match="non-empty user identifier"):
        canonical_actor_iri("")


def test_webfinger_lookup_and_actor_resolution(client, app, test_user):
    """Verify WebFinger resolves username and canonical actor endpoint returns Person."""
    from app.api.federation import _get_domain

    domain = _get_domain()
    with app.app_context():
        user = db.session.get(User, test_user)
        assert user is not None
        canonical_uri = canonical_actor_iri(user.id)

    # Test /.well-known/webfinger
    resp = client.get(f"/.well-known/webfinger?resource=acct:fedtester_v1@{domain}")
    assert resp.status_code == 200
    assert "application/jrd+json" in resp.content_type
    data = resp.get_json()
    assert data["subject"] == f"acct:fedtester_v1@{domain}"
    assert canonical_uri in data["aliases"]
    assert any(link["rel"] == "self" and link["href"] == canonical_uri for link in data["links"])

    # Test /api/federation/webfinger
    resp_api = client.get(f"/api/federation/webfinger?resource=acct:fedtester_v1@{domain}")
    assert resp_api.status_code == 200
    assert resp_api.get_json()["subject"] == f"acct:fedtester_v1@{domain}"

    # Test canonical actor retrieval
    actor_resp = client.get(f"/api/federation/actor/u/{test_user}")
    assert actor_resp.status_code == 200
    assert "application/activity+json" in actor_resp.content_type
    actor_data = actor_resp.get_json()
    assert actor_data["type"] == "Person"
    assert actor_data["id"] == canonical_uri
    assert actor_data["preferredUsername"] == "fedtester_v1"

    # Test legacy username redirect
    legacy_resp = client.get("/api/federation/actor/fedtester_v1")
    assert legacy_resp.status_code == 301
    assert legacy_resp.headers["Location"] == canonical_uri


def test_uri_stability_across_username_update(client, app, test_user):
    """Verify Actor URI remains invariant when user updates their public_username."""
    from app.api.federation import _get_domain

    domain = _get_domain()
    with app.app_context():
        user = db.session.get(User, test_user)
        assert user is not None
        initial_canonical_iri = canonical_actor_iri(user.id)

        # Update username
        user.public_username = "fedtester_v2"
        db.session.commit()

        # Canonical URI is invariant
        post_update_canonical_iri = canonical_actor_iri(user.id)
        assert initial_canonical_iri == post_update_canonical_iri
        db.session.remove()

    # WebFinger for new username resolves to the exact same canonical URI
    resp = client.get(f"/.well-known/webfinger?resource=acct:fedtester_v2@{domain}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["subject"] == f"acct:fedtester_v2@{domain}"
    assert initial_canonical_iri in data["aliases"]
    assert any(link["rel"] == "self" and link["href"] == initial_canonical_iri for link in data["links"])

    # WebFinger lookup using actor URI as resource
    uri_resp = client.get(f"/.well-known/webfinger?resource={initial_canonical_iri}")
    assert uri_resp.status_code == 200
    assert uri_resp.get_json()["subject"] == f"acct:fedtester_v2@{domain}"

    # Canonical actor endpoint reflects new preferredUsername without changing actor ID
    actor_resp = client.get(f"/api/federation/actor/u/{test_user}")
    assert actor_resp.status_code == 200
    actor_data = actor_resp.get_json()
    assert actor_data["id"] == initial_canonical_iri
    assert actor_data["preferredUsername"] == "fedtester_v2"

    # New username route redirects to canonical URI
    new_legacy_resp = client.get("/api/federation/actor/fedtester_v2")
    assert new_legacy_resp.status_code == 301
    assert new_legacy_resp.headers["Location"] == initial_canonical_iri


def test_webfinger_error_cases(client):
    """Verify WebFinger handles missing resource and nonexistent user gracefully."""
    # Missing resource parameter
    resp_empty = client.get("/.well-known/webfinger")
    assert resp_empty.status_code == 400
    assert resp_empty.get_json()["code"] == 400

    # Nonexistent user
    resp_404 = client.get("/.well-known/webfinger?resource=acct:nonexistent_user_999@iqoqo.cc")
    assert resp_404.status_code == 404
    assert resp_404.get_json()["code"] == 404

    # Nonexistent actor UUID
    nonexistent_uuid = uuid.uuid4()
    resp_actor_404 = client.get(f"/api/federation/actor/u/{nonexistent_uuid}")
    assert resp_actor_404.status_code == 404

    # Invalid UUID format
    resp_invalid_uuid = client.get("/api/federation/actor/u/not-a-valid-uuid")
    assert resp_invalid_uuid.status_code == 400
