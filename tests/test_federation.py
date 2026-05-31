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
"""Unit tests for the federation module.

Covers: HTTP signatures, WebFinger, Actor profiles, inbox routing,
trust-level gating, consent enforcement, and SSRF prevention.
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def federation_enabled_app(app):
    """App with federation enabled."""
    app.config["FEDERATION_ENABLED"] = True
    app.config["FEDERATION_BASE_URL"] = "https://test.iqoqo.local"
    return app


@pytest.fixture
def federation_user(app):
    """Create a user with federation consent enabled."""
    from app.db.auth import User
    from app.db.federation import FederationConsent
    from app.db.models import db

    user = User(
        email="feduser@test.local",
        display_name="Fed User",
        public_username="feduser",
        visibility="public",
    )
    db.session.add(user)
    db.session.flush()

    # Generate keypair
    from app.core.federation_keys import generate_actor_keypair

    key_id_suffix, public_key_pem = generate_actor_keypair(str(user.id))
    user.federation_key_id = f"https://test.iqoqo.local/api/federation/actor/feduser{key_id_suffix}"
    user.federation_public_key = public_key_pem

    # Enable federation consent
    consent = FederationConsent(
        user_id=user.id,
        federated_profile=True,
        federated_collection=True,
    )
    db.session.add(consent)
    db.session.commit()

    return user


@pytest.fixture
def non_consenting_user(app):
    """Create a user WITHOUT federation consent."""
    from app.db.auth import User
    from app.db.models import db

    user = User(
        email="nofed@test.local",
        display_name="No Fed",
        public_username="nofeduser",
        visibility="public",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def remote_instance(app):
    """Create a trusted remote federation instance."""
    from app.db.federation import FederationInstance, TrustLevel
    from app.db.models import db

    instance = FederationInstance(
        domain="remote.example.com",
        shared_inbox_url="https://remote.example.com/api/federation/inbox",
        software_name="iqoqo",
        software_version="1.0.0",
        trust_level=TrustLevel.TRUSTED,
        last_seen_at=datetime.now(UTC),
    )
    db.session.add(instance)
    db.session.commit()
    return instance


@pytest.fixture
def remote_actor(app, remote_instance):
    """Create a remote federation actor."""
    from app.db.federation import FederationActor
    from app.db.models import db

    actor = FederationActor(
        actor_uri="https://remote.example.com/api/federation/actor/remoteuser",
        inbox_url="https://remote.example.com/api/federation/actor/remoteuser/inbox",
        outbox_url="https://remote.example.com/api/federation/actor/remoteuser/outbox",
        public_key_pem="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----",
        instance_id=remote_instance.id,
        display_name="Remote User",
        username="remoteuser",
        last_fetched_at=datetime.now(UTC),
    )
    db.session.add(actor)
    db.session.commit()
    return actor


# ---------------------------------------------------------------------------
# HTTP Signature Tests
# ---------------------------------------------------------------------------


class TestHTTPSignatures:
    """Test HTTP signature creation and verification."""

    def test_sign_and_verify_roundtrip(self, app):
        """Signed requests can be verified with the corresponding public key."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        from app.core.http_signatures import sign_request, verify_request

        # Generate keypair
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        from cryptography.hazmat.primitives import serialization

        public_key_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        body = b'{"type": "Follow", "actor": "https://example.com/actor"}'
        url = "https://test.iqoqo.local/api/federation/actor/user/inbox"
        actor_key_id = "https://example.com/actor#main-key"

        # Sign
        headers = sign_request(
            method="POST",
            url=url,
            body=body,
            actor_key_id=actor_key_id,
            private_key=private_key,
        )

        # Verify
        key_id = verify_request(
            method="POST",
            path="/api/federation/actor/user/inbox",
            headers=headers,
            body=body,
            public_key_pem=public_key_pem,
        )

        assert key_id == actor_key_id

    def test_verify_fails_with_wrong_key(self, app):
        """Verification fails when using wrong public key."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        from app.core.http_signatures import SignatureVerificationError, sign_request, verify_request

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        from cryptography.hazmat.primitives import serialization

        wrong_public_pem = (
            wrong_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        body = b'{"type": "Follow"}'
        headers = sign_request(
            method="POST",
            url="https://test.local/inbox",
            body=body,
            actor_key_id="https://example.com/actor#main-key",
            private_key=private_key,
        )

        with pytest.raises(SignatureVerificationError):
            verify_request("POST", "/inbox", headers, body, wrong_public_pem)

    def test_verify_fails_with_tampered_body(self, app):
        """Verification fails when body is tampered after signing."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        from app.core.http_signatures import SignatureVerificationError, sign_request, verify_request

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        body = b'{"type": "Follow"}'
        headers = sign_request(
            method="POST",
            url="https://test.local/inbox",
            body=body,
            actor_key_id="https://example.com/actor#main-key",
            private_key=private_key,
        )

        tampered_body = b'{"type": "Delete"}'
        with pytest.raises(SignatureVerificationError):
            verify_request("POST", "/inbox", headers, tampered_body, public_key_pem)

    def test_verify_fails_without_signature_header(self, app):
        """Verification fails when Signature header is missing."""
        from app.core.http_signatures import SignatureVerificationError, verify_request

        with pytest.raises(SignatureVerificationError, match="Missing Signature header"):
            verify_request("POST", "/inbox", {"Host": "test.local"}, b"{}", "fake_pem")

    def test_sign_get_request_no_digest(self, app):
        """GET requests don't include Digest header."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        from app.core.http_signatures import sign_request

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        headers = sign_request(
            method="GET",
            url="https://test.local/actor",
            body=None,
            actor_key_id="https://example.com/actor#main-key",
            private_key=private_key,
        )

        assert "Digest" not in headers
        assert "Signature" in headers


# ---------------------------------------------------------------------------
# WebFinger Tests
# ---------------------------------------------------------------------------


class TestWebFinger:
    """Test WebFinger endpoint."""

    def test_webfinger_valid_user(self, federation_enabled_app, client, federation_user):
        """WebFinger returns valid JRD for a consenting user."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/.well-known/webfinger?resource=acct:feduser@test.iqoqo.local")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["subject"] == "acct:feduser@test.iqoqo.local"
        assert len(data["links"]) == 1
        assert data["links"][0]["rel"] == "self"
        assert data["links"][0]["type"] == "application/activity+json"
        assert "feduser" in data["links"][0]["href"]

    def test_webfinger_non_consenting_user(self, federation_enabled_app, client, non_consenting_user):
        """WebFinger returns 404 for a user without federation consent."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/.well-known/webfinger?resource=acct:nofeduser@test.iqoqo.local")

        assert response.status_code == 404

    def test_webfinger_invalid_resource(self, federation_enabled_app, client):
        """WebFinger returns 400 for invalid resource format."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/.well-known/webfinger?resource=invalid")

        assert response.status_code == 400

    def test_webfinger_unknown_user(self, federation_enabled_app, client):
        """WebFinger returns 404 for non-existent user."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/.well-known/webfinger?resource=acct:nobody@test.iqoqo.local")

        assert response.status_code == 404

    def test_webfinger_federation_disabled(self, app, client):
        """WebFinger returns 404 when federation is disabled."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": False,
            }.get(k, d)

            response = client.get("/.well-known/webfinger?resource=acct:user@test.local")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Actor Profile Tests
# ---------------------------------------------------------------------------


class TestActorProfile:
    """Test ActivityPub Actor profile endpoint."""

    def test_actor_profile_valid(self, federation_enabled_app, client, federation_user):
        """Actor profile returns valid ActivityPub JSON-LD."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/actor/feduser")

        assert response.status_code == 200
        assert "application/activity+json" in response.content_type

        data = json.loads(response.data)
        assert data["type"] == "Person"
        assert data["preferredUsername"] == "feduser"
        assert "inbox" in data
        assert "outbox" in data
        assert "publicKey" in data
        assert data["publicKey"]["publicKeyPem"].startswith("-----BEGIN PUBLIC KEY-----")
        assert "@context" in data

    def test_actor_profile_non_consenting(self, federation_enabled_app, client, non_consenting_user):
        """Actor profile returns 404 for user without consent."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/actor/nofeduser")

        assert response.status_code == 404

    def test_actor_profile_nonexistent(self, federation_enabled_app, client):
        """Actor profile returns 404 for unknown username."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/actor/nonexistent")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# NodeInfo Tests
# ---------------------------------------------------------------------------


class TestNodeInfo:
    """Test NodeInfo endpoints."""

    def test_nodeinfo_wellknown(self, federation_enabled_app, client):
        """NodeInfo well-known returns link to nodeinfo document."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/.well-known/nodeinfo")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "links" in data
        assert len(data["links"]) == 1
        assert "nodeinfo/2.1" in data["links"][0]["href"]

    def test_nodeinfo_document(self, federation_enabled_app, client):
        """NodeInfo 2.1 document returns valid instance metadata."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/nodeinfo/2.1")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["version"] == "2.1"
        assert data["software"]["name"] == "iqoqo"
        assert "activitypub" in data["protocols"]


# ---------------------------------------------------------------------------
# Inbox Tests
# ---------------------------------------------------------------------------


class TestInbox:
    """Test inbox activity processing."""

    def test_inbox_rejects_without_signature(self, federation_enabled_app, client, federation_user):
        """Inbox returns 401 when no HTTP Signature is provided."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.post(
                "/api/federation/actor/feduser/inbox",
                data=json.dumps({"type": "Follow", "actor": "https://remote.example.com/actor"}),
                content_type="application/activity+json",
            )

        assert response.status_code == 401

    def test_inbox_rejects_oversized_payload(self, federation_enabled_app, client, federation_user):
        """Inbox returns 413 for payloads exceeding size limit."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            # Create oversized payload (> 100KB)
            huge_payload = json.dumps({"type": "Follow", "data": "x" * 200000})
            response = client.post(
                "/api/federation/actor/feduser/inbox",
                data=huge_payload,
                content_type="application/activity+json",
                headers={"Content-Length": str(len(huge_payload))},
            )

        assert response.status_code == 413

    def test_inbox_rejects_blocked_instance(self, federation_enabled_app, client, federation_user, remote_instance):
        """Inbox returns 403 when sending instance is blocked."""
        from app.db.federation import TrustLevel
        from app.db.models import db

        remote_instance.trust_level = TrustLevel.BLOCKED
        db.session.commit()

        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            with patch("app.core.http_signatures.verify_flask_request") as mock_verify:
                mock_verify.return_value = "https://remote.example.com/actor#main-key"

                response = client.post(
                    "/api/federation/actor/feduser/inbox",
                    data=json.dumps(
                        {
                            "type": "Follow",
                            "actor": "https://remote.example.com/api/federation/actor/remoteuser",
                            "object": "https://test.iqoqo.local/api/federation/actor/feduser",
                        }
                    ),
                    content_type="application/activity+json",
                )

        assert response.status_code == 403

    def test_shared_inbox_rejects_without_signature(self, federation_enabled_app, client):
        """Shared inbox also requires HTTP Signature."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.post(
                "/api/federation/inbox",
                data=json.dumps({"type": "Follow", "actor": "https://remote.example.com/actor"}),
                content_type="application/activity+json",
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Outbox Tests
# ---------------------------------------------------------------------------


class TestOutbox:
    """Test outbox endpoint."""

    def test_outbox_returns_collection(self, federation_enabled_app, client, federation_user):
        """Outbox returns an OrderedCollection."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/actor/feduser/outbox")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["type"] == "OrderedCollection"
        assert "totalItems" in data

    def test_outbox_non_consenting_user(self, federation_enabled_app, client, non_consenting_user):
        """Outbox returns 404 for non-consenting user."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/actor/nofeduser/outbox")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# SSRF Prevention Tests
# ---------------------------------------------------------------------------


class TestSSRFPrevention:
    """Test SSRF prevention in federation client."""

    def test_blocks_private_ip(self, app):
        """Federation client blocks requests to private IPs."""
        from app.core.federation_client import SSRFError, _validate_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.1", 443))]
            with pytest.raises(SSRFError, match="private IP"):
                _validate_url("https://evil.com/actor")

    def test_blocks_loopback(self, app):
        """Federation client blocks requests to loopback addresses."""
        from app.core.federation_client import SSRFError, _validate_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
            with pytest.raises(SSRFError, match="private IP"):
                _validate_url("https://evil.com/actor")

    def test_blocks_aws_imds(self, app):
        """Federation client blocks requests to AWS IMDS endpoint."""
        from app.core.federation_client import SSRFError, _validate_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("169.254.169.254", 80))]
            with pytest.raises(SSRFError, match="private IP"):
                _validate_url("http://169.254.169.254/latest/meta-data/")

    def test_blocks_link_local(self, app):
        """Federation client blocks link-local addresses."""
        from app.core.federation_client import SSRFError, _validate_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("169.254.1.1", 443))]
            with pytest.raises(SSRFError, match="private IP"):
                _validate_url("https://evil.com/actor")

    def test_allows_public_ip(self, app):
        """Federation client allows requests to public IPs."""
        from app.core.federation_client import _validate_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 443))]
            # Should not raise
            _validate_url("https://example.com/actor")

    def test_blocks_invalid_scheme(self, app):
        """Federation client blocks non-HTTP(S) schemes."""
        from app.core.federation_client import SSRFError, _validate_url

        with pytest.raises(SSRFError, match="Invalid URL scheme"):
            _validate_url("ftp://evil.com/file")


# ---------------------------------------------------------------------------
# Key Management Tests
# ---------------------------------------------------------------------------


class TestKeyManagement:
    """Test RSA key generation and management."""

    def test_generate_keypair(self, app, tmp_path):
        """Generate keypair creates valid RSA keys."""
        import os

        os.environ["FEDERATION_KEYS_DIR"] = str(tmp_path)

        # Reload to pick up env var
        from app.core import federation_keys

        federation_keys._KEYS_DIR = tmp_path

        user_id = str(uuid.uuid4())
        key_id_suffix, public_key_pem = federation_keys.generate_actor_keypair(user_id)

        assert key_id_suffix == "#main-key"
        assert public_key_pem.startswith("-----BEGIN PUBLIC KEY-----")
        assert (tmp_path / f"{user_id}.pem").exists()

    def test_get_private_key(self, app, tmp_path):
        """Can retrieve generated private key."""
        from app.core import federation_keys

        federation_keys._KEYS_DIR = tmp_path

        user_id = str(uuid.uuid4())
        federation_keys.generate_actor_keypair(user_id)

        private_key = federation_keys.get_actor_private_key(user_id)
        assert private_key is not None

    def test_get_public_key(self, app, tmp_path):
        """Can derive public key from private key."""
        from app.core import federation_keys

        federation_keys._KEYS_DIR = tmp_path

        user_id = str(uuid.uuid4())
        federation_keys.generate_actor_keypair(user_id)

        public_key = federation_keys.get_actor_public_key(user_id)
        assert public_key is not None
        assert "BEGIN PUBLIC KEY" in public_key

    def test_delete_keypair(self, app, tmp_path):
        """Delete keypair removes the key file."""
        from app.core import federation_keys

        federation_keys._KEYS_DIR = tmp_path

        user_id = str(uuid.uuid4())
        federation_keys.generate_actor_keypair(user_id)

        assert federation_keys.delete_actor_keypair(user_id) is True
        assert federation_keys.get_actor_private_key(user_id) is None

    def test_get_nonexistent_key(self, app, tmp_path):
        """Getting a key for a user with no keypair returns None."""
        from app.core import federation_keys

        federation_keys._KEYS_DIR = tmp_path

        assert federation_keys.get_actor_private_key("nonexistent") is None
        assert federation_keys.get_actor_public_key("nonexistent") is None


# ---------------------------------------------------------------------------
# Activity Handler Tests
# ---------------------------------------------------------------------------


class TestActivityHandlers:
    """Test inbound activity routing and handling."""

    def test_handle_follow(self, app, federation_user, remote_instance, remote_actor):
        """Follow activity creates a pending follower record."""
        from app.core.federation_handlers import handle_follow
        from app.db.federation import FederationFollower, FollowStatus
        from app.db.models import db

        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
                "FEDERATION_AUTO_ACCEPT_FOLLOWS": False,
                "FEDERATION_DEFAULT_TRUST": "untrusted",
            }.get(k, d)

            activity = {
                "type": "Follow",
                "actor": "https://remote.example.com/api/federation/actor/remoteuser",
                "object": "https://test.iqoqo.local/api/federation/actor/feduser",
            }

            result = handle_follow(activity)

        assert result is True
        follower = FederationFollower.query.filter_by(local_user_id=federation_user.id).first()
        assert follower is not None
        assert follower.status == FollowStatus.PENDING

    def test_handle_undo_follow(self, app, federation_user, remote_actor):
        """Undo(Follow) removes the follower relationship."""
        from app.core.federation_handlers import handle_activity
        from app.db.federation import FederationFollower, FollowStatus
        from app.db.models import db

        # Create existing follower
        follower = FederationFollower(
            local_user_id=federation_user.id,
            remote_actor_id=remote_actor.id,
            status=FollowStatus.ACCEPTED,
        )
        db.session.add(follower)
        db.session.commit()

        activity = {
            "type": "Undo",
            "actor": "https://remote.example.com/api/federation/actor/remoteuser",
            "object": {
                "type": "Follow",
                "actor": "https://remote.example.com/api/federation/actor/remoteuser",
                "object": "https://test.iqoqo.local/api/federation/actor/feduser",
            },
        }

        result = handle_activity(activity)
        assert result is True

        remaining = FederationFollower.query.filter_by(local_user_id=federation_user.id).first()
        assert remaining is None

    def test_handle_create_untrusted(self, app, federation_user):
        """Create activity from untrusted instance is ignored."""
        from app.core.federation_handlers import handle_create
        from app.db.federation import FederationInstance, TrustLevel
        from app.db.models import db

        instance = FederationInstance(
            domain="untrusted.example.com",
            trust_level=TrustLevel.UNTRUSTED,
        )
        db.session.add(instance)
        db.session.commit()

        activity = {
            "type": "Create",
            "actor": "https://untrusted.example.com/actor",
            "object": {"type": "Note", "content": "Hello"},
        }

        result = handle_create(activity)
        assert result is False

    def test_handle_unknown_type(self, app):
        """Unknown activity type returns False."""
        from app.core.federation_handlers import handle_activity

        result = handle_activity({"type": "UnknownType", "actor": "https://x.com/a"})
        assert result is False


# ---------------------------------------------------------------------------
# Federation Guard Tests
# ---------------------------------------------------------------------------


class TestFederationGuard:
    """Test the @federation_required decorator."""

    def test_guard_blocks_when_disabled(self, app, client):
        """Guard returns 404 when federation is disabled."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.return_value = False
            response = client.get("/.well-known/webfinger?resource=acct:u@test.local")

        assert response.status_code == 404

    def test_guard_allows_when_enabled(self, federation_enabled_app, client, federation_user):
        """Guard allows request when federation is enabled."""
        with patch("app.core.config_service.ConfigService.get") as mock_get:
            mock_get.side_effect = lambda k, d=None: {
                "FEDERATION_ENABLED": True,
                "FEDERATION_BASE_URL": "https://test.iqoqo.local",
            }.get(k, d)

            response = client.get("/api/federation/nodeinfo/2.1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Admin Federation API Tests
# ---------------------------------------------------------------------------


class TestAdminFederationAPI:
    """Test admin federation instance management endpoints."""

    def test_list_instances(self, app, client, admin_headers, remote_instance):
        """Admin can list federation instances."""
        response = client.get("/api/v1/admin/federation/instances", headers=admin_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["data"]) >= 1

    def test_update_trust_level(self, app, client, admin_headers, remote_instance):
        """Admin can change instance trust level."""
        response = client.put(
            f"/api/v1/admin/federation/instances/{remote_instance.id}/trust",
            headers=admin_headers,
            data=json.dumps({"trust_level": "blocked"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["trust_level"] == "blocked"

    def test_update_trust_invalid_level(self, app, client, admin_headers, remote_instance):
        """Admin gets error for invalid trust level."""
        response = client.put(
            f"/api/v1/admin/federation/instances/{remote_instance.id}/trust",
            headers=admin_headers,
            data=json.dumps({"trust_level": "super_trusted"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_delete_instance(self, app, client, admin_headers, remote_instance):
        """Admin can delete an instance."""
        response = client.delete(
            f"/api/v1/admin/federation/instances/{remote_instance.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["data"]["deleted"] is True

    def test_list_activities(self, app, client, admin_headers):
        """Admin can list federation activities."""
        response = client.get("/api/v1/admin/federation/activities", headers=admin_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "pagination" in data


# ---------------------------------------------------------------------------
# Discovery Tests
# ---------------------------------------------------------------------------


class TestFederationDiscovery:
    """Test instance discovery."""

    def test_discover_known_instance(self, app, remote_instance):
        """Discovery returns existing instance if already known."""
        from app.core.federation_discovery import discover_instance

        result = discover_instance("remote.example.com")
        assert result is not None
        assert result.id == remote_instance.id

    def test_discover_new_instance(self, app):
        """Discovery creates new instance from NodeInfo."""
        from app.core.federation_discovery import discover_instance

        with patch("app.core.federation_client.federation_client.fetch_nodeinfo") as mock_fetch:
            mock_fetch.return_value = {
                "version": "2.1",
                "software": {"name": "iqoqo", "version": "1.0.0"},
                "protocols": ["activitypub"],
            }

            with patch("app.core.config_service.ConfigService.get") as mock_config:
                mock_config.return_value = "untrusted"
                result = discover_instance("new.example.com")

        assert result is not None
        assert result.domain == "new.example.com"
        assert result.software_name == "iqoqo"

    def test_discover_non_activitypub_instance(self, app):
        """Discovery returns None for non-ActivityPub instance."""
        from app.core.federation_discovery import discover_instance

        with patch("app.core.federation_client.federation_client.fetch_nodeinfo") as mock_fetch:
            mock_fetch.return_value = {
                "version": "2.1",
                "software": {"name": "wordpress", "version": "6.0"},
                "protocols": ["atom"],
            }

            result = discover_instance("blog.example.com")

        assert result is None


# ---------------------------------------------------------------------------
# Sync Tests
# ---------------------------------------------------------------------------


class TestFederationSync:
    """Test metadata synchronization."""

    def test_sync_blocked_instance(self, app, remote_instance):
        """Sync rejects data from blocked instances."""
        from app.core.federation_sync import sync_remote_object
        from app.db.federation import TrustLevel
        from app.db.models import db

        remote_instance.trust_level = TrustLevel.BLOCKED
        db.session.commit()

        result = sync_remote_object({"type": "Document"}, remote_instance)
        assert result is False

    def test_sync_pending_instance_queues_review(self, app, remote_instance):
        """Sync from pending instance queues for admin review."""
        from app.core.federation_sync import sync_remote_object
        from app.db.federation import FederationActivity, TrustLevel
        from app.db.models import db

        remote_instance.trust_level = TrustLevel.PENDING
        db.session.commit()

        result = sync_remote_object({"type": "Document", "id": "urn:test"}, remote_instance)
        assert result is True

        # Check activity was queued
        pending = FederationActivity.query.filter_by(activity_type="PendingMerge").first()
        assert pending is not None

    def test_sync_trusted_instance_auto_merges(self, app, remote_instance):
        """Sync from trusted instance auto-merges."""
        from app.core.federation_sync import sync_remote_object

        result = sync_remote_object({"type": "Document", "id": "urn:test"}, remote_instance)
        assert result is True


# ---------------------------------------------------------------------------
# Consent API Tests
# ---------------------------------------------------------------------------


class TestConsentAPI:
    """Test user consent GET/PUT endpoints."""

    def test_get_consent_unauthenticated(self, federation_enabled_app):
        """GET /federation/consent without auth returns 401."""
        with federation_enabled_app.test_client() as client:
            resp = client.get("/api/federation/consent")
            assert resp.status_code == 401

    def test_get_consent_default(self, federation_enabled_app, non_consenting_user):
        """GET /federation/consent returns defaults when no record exists."""
        from app.api.auth import generate_internal_jwt

        with federation_enabled_app.test_client() as client:
            token = generate_internal_jwt(non_consenting_user)
            resp = client.get("/api/federation/consent", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["federated_profile"] is False
            assert data["data"]["federated_collection"] is False

    def test_put_consent_enables_federation(self, federation_enabled_app, non_consenting_user):
        """PUT /federation/consent creates consent and generates keypair."""
        from app.api.auth import generate_internal_jwt

        with federation_enabled_app.test_client() as client:
            token = generate_internal_jwt(non_consenting_user)
            resp = client.put(
                "/api/federation/consent",
                json={"federated_profile": True},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["federated_profile"] is True

            # Verify keypair was generated
            from app.core.federation_keys import get_actor_public_key

            pub_key = get_actor_public_key(str(non_consenting_user.id))
            assert pub_key is not None
            assert "BEGIN PUBLIC KEY" in pub_key

    def test_put_consent_no_body(self, federation_enabled_app, federation_user):
        """PUT /federation/consent with no body returns 400."""
        from app.api.auth import generate_internal_jwt

        with federation_enabled_app.test_client() as client:
            token = generate_internal_jwt(federation_user)
            resp = client.put(
                "/api/federation/consent",
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
            assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Date Header Replay Protection Tests
# ---------------------------------------------------------------------------


class TestDateHeaderReplayProtection:
    """Test that stale Date headers are rejected."""

    def test_stale_date_rejected(self, federation_enabled_app, federation_user, remote_actor):
        """Inbox rejects requests with Date header older than 5 minutes."""
        from email.utils import formatdate
        from time import mktime

        # Sign with a date 10 minutes in the past
        from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

        from app.core.http_signatures import sign_request

        private_key = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = private_key.public_key().public_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.PEM,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.SubjectPublicKeyInfo,
        )

        # Update remote actor with the real public key
        from app.db.models import db

        remote_actor.public_key_pem = public_pem.decode("utf-8")
        db.session.commit()

        # Create an activity with a stale date
        from datetime import timedelta

        stale_time = datetime.now(UTC) - timedelta(minutes=10)
        stale_date = formatdate(timeval=mktime(stale_time.timetuple()), localtime=False, usegmt=True)

        activity = {"type": "Follow", "actor": remote_actor.actor_uri, "object": "https://test.iqoqo.local/api/federation/actor/feduser"}
        body = json.dumps(activity).encode()
        sig_headers = sign_request(
            method="POST",
            url="https://test.iqoqo.local/api/federation/actor/feduser/inbox",
            body=body,
            actor_key_id=f"{remote_actor.actor_uri}#main-key",
            private_key=private_key,
        )
        # Override Date header with stale value
        sig_headers["Date"] = stale_date

        with federation_enabled_app.test_client() as client:
            resp = client.post(
                "/api/federation/actor/feduser/inbox",
                data=body,
                headers=sig_headers,
                content_type="application/activity+json",
            )
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Remote Actor Key Fetch Tests
# ---------------------------------------------------------------------------


class TestRemoteActorKeyFetch:
    """Test that unknown actors' keys are fetched on first contact."""

    def test_unknown_actor_key_fetched(self, federation_enabled_app, remote_instance, federation_user):
        """verify_flask_request fetches actor profile when key is missing."""
        from unittest.mock import MagicMock, patch

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

        # Generate a real keypair
        private_key = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        actor_uri = "https://remote.example.com/api/federation/actor/newuser"

        # Mock the federation client to return actor profile with public key
        mock_actor_data = {
            "id": actor_uri,
            "type": "Person",
            "preferredUsername": "newuser",
            "name": "New User",
            "inbox": f"{actor_uri}/inbox",
            "outbox": f"{actor_uri}/outbox",
            "publicKey": {
                "id": f"{actor_uri}#main-key",
                "owner": actor_uri,
                "publicKeyPem": public_pem,
            },
        }

        with federation_enabled_app.app_context():
            from app.core.http_signatures import sign_request

            # Sign a request
            activity = {"type": "Follow", "actor": actor_uri, "object": "https://test.iqoqo.local/api/federation/actor/feduser"}
            body = json.dumps(activity).encode()
            sig_headers = sign_request(
                method="POST",
                url="https://test.iqoqo.local/api/federation/actor/feduser/inbox",
                body=body,
                actor_key_id=f"{actor_uri}#main-key",
                private_key=private_key,
            )

            with patch("app.core.federation_client.federation_client.fetch_actor", return_value=mock_actor_data):
                with federation_enabled_app.test_client() as client:
                    resp = client.post(
                        "/api/federation/actor/feduser/inbox",
                        data=body,
                        headers=sig_headers,
                        content_type="application/activity+json",
                    )
                    # Should succeed (202 accepted) — actor was fetched and key cached
                    assert resp.status_code == 202

            # Verify actor was cached in DB
            from app.db.federation import FederationActor

            cached = FederationActor.query.filter_by(actor_uri=actor_uri).first()
            assert cached is not None
            assert cached.public_key_pem == public_pem
            assert cached.username == "newuser"

    def test_fetch_failure_returns_401(self, federation_enabled_app):
        """verify_flask_request returns 401 when actor fetch fails."""
        from unittest.mock import patch

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

        from app.core.federation_client import FederationDeliveryError
        from app.core.http_signatures import sign_request

        private_key = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
        actor_uri = "https://unreachable.example.com/actor/ghost"

        activity = {"type": "Follow", "actor": actor_uri, "object": "x"}
        body = json.dumps(activity).encode()
        sig_headers = sign_request(
            method="POST",
            url="https://test.iqoqo.local/api/federation/inbox",
            body=body,
            actor_key_id=f"{actor_uri}#main-key",
            private_key=private_key,
        )

        with patch(
            "app.core.federation_client.federation_client.fetch_actor",
            side_effect=FederationDeliveryError("Connection refused"),
        ):
            with federation_enabled_app.test_client() as client:
                resp = client.post(
                    "/api/federation/inbox",
                    data=body,
                    headers=sig_headers,
                    content_type="application/activity+json",
                )
                assert resp.status_code == 401
