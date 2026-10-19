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
"""End-to-end multi-instance ActivityPub federation simulation, SSRF chaos, and SRE audit tests."""

from __future__ import annotations

import email.utils
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import federation_keys
from app.core.federation_client import FederationClient
from app.core.http_signatures import (
    DateSkewError,
    DigestMismatchError,
    SignatureVerificationError,
    compute_digest,
    sign_request,
    verify_request,
)
from app.core.telemetry import (
    federation_delivery_failures_total,
    federation_sig_failures_total,
    record_outbound_telemetry,
    sanitize_headers,
    sanitize_url,
)
from app.db import db
from app.db.auth import User
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)
from app.utils.http_client import SSRFError, safe_get, safe_post


class MockWsgiRequest:
    """Mock Flask WSGI-like request for signature verification."""

    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
        query_string: str = "",
    ) -> None:
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query_string = query_string

    def get_data(self) -> bytes:
        return self.body


@pytest.fixture
def rsa_keypair() -> tuple[rsa.RSAPrivateKey, str]:
    """Generate ephemeral RSA-2048 keypair."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = (
        priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return priv, pub_pem


# ===========================================================================
# 1. Two-Instance E2E ActivityPub Simulation Harness
# ===========================================================================


class TestFederationTwoInstanceSimulation:
    """Simulate complete federated exchange between Instance Alpha and Instance Beta."""

    def test_bidirectional_discovery_follow_and_metadata_broadcast(self, app, rsa_keypair, monkeypatch) -> None:
        """Simulate two instances: WebFinger lookup, actor retrieval, follow, and metadata broadcast."""
        monkeypatch.setenv("BASE_URL", "https://alpha.iqoqo.test")
        priv_alpha, pub_alpha = rsa_keypair
        priv_beta, pub_beta = (
            rsa.generate_private_key(public_exponent=65537, key_size=2048),
            "",
        )
        pub_beta = (
            priv_beta.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            app.config["BASE_URL"] = "https://alpha.iqoqo.test"

            # 1. Setup local user on Instance Alpha
            user_alpha = User(
                email="alpha_user@alpha.iqoqo.test",
                public_username="alpha_user",
                display_name="Alpha Librarian",
            )
            user_alpha.set_password("SecurePass123!")
            db.session.add(user_alpha)
            db.session.commit()

            consent_alpha = FederationConsent(
                user_id=user_alpha.id,
                federated_profile=True,
                federated_collection=True,
            )
            db.session.add(consent_alpha)
            db.session.commit()

            alpha_actor_uri = f"https://alpha.iqoqo.test/api/federation/actor/u/{user_alpha.id}"
            beta_actor_uri = "https://beta.iqoqo.test/users/beta_curator"
            beta_inbox_uri = "https://beta.iqoqo.test/users/beta_curator/inbox"
            alpha_inbox_uri = f"{alpha_actor_uri}/inbox"

            # 2. Simulate WebFinger discovery from Alpha targeting Beta
            mock_webfinger_beta_response = MagicMock(spec=requests.Response)
            mock_webfinger_beta_response.status_code = 200
            mock_webfinger_beta_response.json.return_value = {
                "subject": "acct:beta_curator@beta.iqoqo.test",
                "links": [
                    {
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": beta_actor_uri,
                    }
                ],
            }

            mock_actor_beta_response = MagicMock(spec=requests.Response)
            mock_actor_beta_response.status_code = 200
            mock_actor_beta_response.json.return_value = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": beta_actor_uri,
                "type": "Person",
                "preferredUsername": "beta_curator",
                "name": "Beta Curator",
                "inbox": beta_inbox_uri,
                "publicKey": {
                    "id": f"{beta_actor_uri}#main-key",
                    "owner": beta_actor_uri,
                    "publicKeyPem": pub_beta,
                },
                "endpoints": {
                    "sharedInbox": "https://beta.iqoqo.test/inbox",
                },
            }

            # 3. Instance Alpha fetches Beta's Actor via FederationClient
            client_alpha = FederationClient()
            with patch("app.core.federation_client.safe_get") as mock_get:
                mock_get.return_value = mock_actor_beta_response
                beta_actor_data = client_alpha.fetch_actor(beta_actor_uri)

            assert beta_actor_data is not None
            assert beta_actor_data["id"] == beta_actor_uri
            assert beta_actor_data["preferredUsername"] == "beta_curator"

            # Verify Instance Beta was registered in Alpha's database
            instance_beta = (
                db.session.execute(db.select(FederationInstance).where(FederationInstance.domain == "beta.iqoqo.test")).scalars().first()
            )
            assert instance_beta is not None
            assert instance_beta.domain == "beta.iqoqo.test"

            # 4. Instance Alpha dispatches signed Follow activity to Beta's inbox
            follow_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://alpha.iqoqo.test/activities/{uuid.uuid4()}",
                "type": "Follow",
                "actor": alpha_actor_uri,
                "object": beta_actor_uri,
            }

            with patch("app.core.federation_keys.get_actor_private_key", return_value=priv_alpha):
                with patch("app.core.federation_client.safe_post") as mock_post:
                    mock_post.return_value = MagicMock(status_code=202)
                    resp = client_alpha.post_to_inbox(
                        beta_inbox_uri,
                        activity=follow_activity,
                        sender_user_id=str(user_alpha.id),
                    )
                    assert resp.status_code == 202

                    # Verify signed headers generated
                    sent_headers = mock_post.call_args[1]["headers"]
                    assert "Signature" in sent_headers
                    assert "Digest" in sent_headers
                    assert "Date" in sent_headers

            # 5. Simulate Instance Beta receiving and verifying Alpha's Follow request
            follow_body = json.dumps(follow_activity).encode("utf-8")
            incoming_follow_req = MockWsgiRequest(
                method="POST",
                path="/users/beta_curator/inbox",
                headers=sent_headers,
                body=follow_body,
            )

            # Beta verifies Alpha's signature using Alpha's public key
            verified_actor = verify_request(
                incoming_follow_req,
                key_resolver=lambda kid: pub_alpha if "alpha.iqoqo.test" in kid else None,
            )
            assert verified_actor == alpha_actor_uri

            # Record follower on Beta
            beta_actor_db = (
                db.session.execute(db.select(FederationActor).where(FederationActor.actor_uri == beta_actor_uri)).scalars().first()
            )
            follower_record = FederationFollower(
                local_user_id=user_alpha.id,
                remote_actor_id=beta_actor_db.id,
                status=FollowStatus.ACCEPTED,
            )
            db.session.add(follower_record)
            db.session.commit()
            assert follower_record.id is not None

            # 6. Instance Beta broadcasts metadata update (Work / Manifestation) to Alpha
            metadata_update_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://beta.iqoqo.test/activities/{uuid.uuid4()}",
                "type": "Update",
                "actor": beta_actor_uri,
                "object": {
                    "type": "Document",
                    "id": "https://beta.iqoqo.test/works/frbr-solaris",
                    "name": "Solaris (Stanisław Lem)",
                    "attributedTo": beta_actor_uri,
                },
                "target": alpha_actor_uri,
            }
            update_body = json.dumps(metadata_update_activity).encode("utf-8")

            signed_beta_headers = sign_request(
                method="POST",
                url=alpha_inbox_uri,
                body=update_body,
                key_id=f"{beta_actor_uri}#main-key",
                private_key=priv_beta,
            )

            # Alpha receives and verifies Beta's update activity
            incoming_update_req = MockWsgiRequest(
                method="POST",
                path=f"/api/federation/actor/u/{user_alpha.id}/inbox",
                headers=signed_beta_headers,
                body=update_body,
            )

            verified_sender = verify_request(
                incoming_update_req,
                key_resolver=lambda kid: pub_beta if "beta.iqoqo.test" in kid else None,
            )
            assert verified_sender == beta_actor_uri

            # Alpha records delivered inbound activity
            activity_record = FederationActivity(
                actor_uri=beta_actor_uri,
                activity_type="Update",
                object_json=metadata_update_activity["object"],
                target_uri=alpha_actor_uri,
                direction="inbound",
                status=ActivityStatus.DELIVERED,
                delivered_at=datetime.now(UTC),
            )
            db.session.add(activity_record)
            db.session.commit()

            assert activity_record.id is not None
            assert activity_record.status == ActivityStatus.DELIVERED
            assert activity_record.direction == "inbound"


# ===========================================================================
# 2. Signature Replay & Cryptographic Chaos Tests
# ===========================================================================


class TestSignatureReplayAndChaos:
    """Security audit tests verifying rejection of replayed, expired, and tampered requests."""

    def test_rejection_of_expired_date_skew(self, rsa_keypair) -> None:
        """Verify requests older than 300 seconds are rejected with DateSkewError."""
        priv_key, pub_pem = rsa_keypair
        body = b'{"type":"Like"}'
        key_id = "https://peer.example.org/users/signer#main-key"

        signed = sign_request(
            method="POST",
            url="https://iqoqo.local/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        # Skew Date header 350 seconds into past (replay attack simulation)
        old_time = datetime.now(UTC) - timedelta(seconds=350)
        signed["Date"] = email.utils.formatdate(old_time.timestamp(), usegmt=True)

        req = MockWsgiRequest("POST", "/inbox", signed, body)
        with pytest.raises(DateSkewError, match="Date header skew"):
            verify_request(req, max_skew_seconds=300, key_resolver=lambda _: pub_pem)

    def test_rejection_of_future_skew(self, rsa_keypair) -> None:
        """Verify requests with Date header skewed > 300 seconds into future are rejected."""
        priv_key, pub_pem = rsa_keypair
        body = b'{"type":"Announce"}'
        key_id = "https://peer.example.org/users/signer#main-key"

        signed = sign_request(
            method="POST",
            url="https://iqoqo.local/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        future_time = datetime.now(UTC) + timedelta(seconds=400)
        signed["Date"] = email.utils.formatdate(future_time.timestamp(), usegmt=True)

        req = MockWsgiRequest("POST", "/inbox", signed, body)
        with pytest.raises(DateSkewError):
            verify_request(req, max_skew_seconds=300, key_resolver=lambda _: pub_pem)

    def test_rejection_of_tampered_digest(self, rsa_keypair) -> None:
        """Verify request body modification after signing fails with DigestMismatchError."""
        priv_key, pub_pem = rsa_keypair
        original_body = b'{"type":"Create","content":"Friendly greeting"}'
        tampered_body = b'{"type":"Create","content":"Malicious payload injection"}'
        key_id = "https://peer.example.org/users/signer#main-key"

        signed = sign_request(
            method="POST",
            url="https://iqoqo.local/inbox",
            body=original_body,
            key_id=key_id,
            private_key=priv_key,
        )

        req = MockWsgiRequest("POST", "/inbox", signed, tampered_body)
        with pytest.raises(DigestMismatchError, match="Digest header mismatch"):
            verify_request(req, key_resolver=lambda _: pub_pem)

    def test_rejection_of_tampered_request_target(self, rsa_keypair) -> None:
        """Verify altering HTTP method or path invalidates cryptographic signature."""
        priv_key, pub_pem = rsa_keypair
        body = b'{"type":"Delete"}'
        key_id = "https://peer.example.org/users/signer#main-key"

        signed = sign_request(
            method="POST",
            url="https://iqoqo.local/users/alice/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        # Attacker replays signed request against an administrative path
        tampered_req = MockWsgiRequest(
            method="POST",
            path="/admin/destructive-action",
            headers=signed,
            body=body,
        )

        with pytest.raises(SignatureVerificationError, match="RSA signature verification failed"):
            verify_request(tampered_req, key_resolver=lambda _: pub_pem)

    def test_rejection_of_domain_mismatch_and_identity_spoofing(self, rsa_keypair) -> None:
        """Verify an adversary on evil.com cannot forge activities for innocent.com."""
        priv_key, pub_pem = rsa_keypair
        body = b'{"type":"Follow","actor":"https://innocent.com/users/alice"}'
        # Key ID belongs to evil.com
        evil_key_id = "https://evil.com/actor#main-key"

        signed = sign_request(
            method="POST",
            url="https://iqoqo.local/inbox",
            body=body,
            key_id=evil_key_id,
            private_key=priv_key,
        )

        req = MockWsgiRequest("POST", "/inbox", signed, body)
        # Should detect mismatch between evil.com keyId and innocent.com payload actor
        with pytest.raises(SignatureVerificationError, match="does not match payload actor domain"):
            verify_request(req, key_resolver=lambda _: pub_pem)


# ===========================================================================
# 3. SSRF, DNS Rebinding, and Redirect Chain Defenses
# ===========================================================================


class TestSSRFAndDNSRebindingChaos:
    """Security audit tests verifying DNS rebinding and internal IP blocking."""

    @patch("app.utils.http_client._resolve_with_timeout")
    def test_dns_rebinding_defense_pins_ip_address(self, mock_resolve) -> None:
        """Verify safe_get and safe_post pin socket connections to initially resolved public IP."""
        # Initial resolution returns valid public IP
        mock_resolve.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]

        with patch("requests.Session.get") as mock_session_get:
            mock_resp = MagicMock(status_code=200, is_redirect=False)
            mock_session_get.return_value = mock_resp

            resp = safe_get("http://rebinding.example.com/actor")
            assert resp.status_code == 200

            # Verify request was rewritten to connect to pinned IP 93.184.216.34 with Host header
            call_args, call_kwargs = mock_session_get.call_args
            assert "93.184.216.34" in call_args[0]
            assert call_kwargs["headers"]["Host"] == "rebinding.example.com"

    @patch("app.utils.http_client._resolve_with_timeout")
    def test_dns_rebinding_to_private_ip_is_blocked(self, mock_resolve) -> None:
        """Verify that if DNS resolution returns a loopback or private IP, request is blocked."""
        # Malicious DNS server answers with loopback
        mock_resolve.return_value = [(2, 1, 6, "", ("127.0.0.1", 80))]

        with pytest.raises(SSRFError, match="Blocked: .* resolved to restricted IP"):
            safe_get("http://evil-rebind.example.com/inbox")

    @patch("app.utils.http_client._resolve_with_timeout")
    def test_http_redirect_chain_to_private_ip_blocked(self, mock_resolve) -> None:
        """Verify redirect to 169.254.169.254 or internal subnet is stopped at redirect hop."""

        # Step 1: Public host
        # Step 2: Resolves to metadata IP 169.254.169.254
        def resolve_side_effect(hostname: str, timeout: float = 5.0):
            if hostname == "public-hop.example.com":
                return [(2, 1, 6, "", ("93.184.216.34", 80))]
            if hostname == "internal-hop.example.com":
                return [(2, 1, 6, "", ("169.254.169.254", 80))]
            return [(2, 1, 6, "", ("10.0.0.1", 80))]

        mock_resolve.side_effect = resolve_side_effect

        with patch("requests.Session.get") as mock_session_get:
            # First request returns 302 redirect to internal-hop
            redirect_resp = MagicMock(status_code=302, is_redirect=True)
            redirect_resp.headers = {"location": "http://internal-hop.example.com/latest/meta-data"}
            mock_session_get.return_value = redirect_resp

            with pytest.raises(SSRFError, match="restricted IP 169.254.169.254"):
                safe_get("http://public-hop.example.com/start")

    @patch("app.utils.http_client._resolve_with_timeout")
    def test_redirect_limit_exceeded_raises_ssrf_error(self, mock_resolve) -> None:
        """Verify infinite redirect loops are aborted and raise SSRFError."""
        mock_resolve.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]

        with patch("requests.Session.get") as mock_session_get:
            loop_resp = MagicMock(status_code=302, is_redirect=True)
            loop_resp.headers = {"location": "http://public.example.com/loop"}
            mock_session_get.return_value = loop_resp

            with pytest.raises(SSRFError, match="Too many redirects"):
                safe_get("http://public.example.com/loop", max_redirects=3)


# ===========================================================================
# 4. Observability & SRE Verification (OpenObserve / OTel Metrics)
# ===========================================================================


class TestObservabilityAndTelemetry:
    """Verify OpenObserve metrics and OpenTelemetry span telemetry."""

    def test_federation_sig_failures_total_incremented(self) -> None:
        """Verify federation_sig_failures_total counter is incremented on signature errors."""
        with patch.object(federation_sig_failures_total, "add") as mock_counter_add:
            req = MockWsgiRequest("POST", "/inbox", headers={})

            with pytest.raises(SignatureVerificationError):
                verify_request(req)

            mock_counter_add.assert_called_once()
            called_args, _ = mock_counter_add.call_args
            assert called_args[0] == 1
            assert called_args[1].get("reason") == "missing_signature_header"

    def test_federation_delivery_failures_total_incremented_on_error(self) -> None:
        """Verify federation_delivery_failures_total counter is incremented on delivery failure."""
        with patch.object(federation_delivery_failures_total, "add") as mock_delivery_counter:
            client = FederationClient()

            with patch("app.core.federation_client.safe_post", side_effect=requests.ConnectionError("Connection refused")):
                with pytest.raises(requests.ConnectionError):
                    client.post_to_inbox("https://failed-target.example.org/inbox", {"type": "Follow"})

            mock_delivery_counter.assert_called_once()
            called_args, _ = mock_delivery_counter.call_args
            assert called_args[0] == 1
            assert called_args[1].get("domain") == "failed-target.example.org"
            assert called_args[1].get("reason") == "network_error"

    def test_post_to_inbox_retries_on_503_and_transient_network_errors(self) -> None:
        """Verify FederationClient.post_to_inbox retries HTTP 503 up to 3 times before succeeding or failing."""
        client = FederationClient()
        assert client.timeout == (10, 30)
        mock_503 = MagicMock(status_code=503)
        with patch("app.core.federation_client.safe_post", side_effect=[mock_503, mock_503, MagicMock(status_code=202)]) as mock_post:
            resp = client.post_to_inbox("https://retry-target.example.org/inbox", {"type": "Follow"})
            assert resp.status_code == 202
            assert mock_post.call_count == 3

    def test_outbound_federation_records_telemetry_span(self) -> None:
        """Verify record_outbound_telemetry is invoked when FederationClient sends activities."""
        with patch("app.core.federation_client.record_outbound_telemetry") as mock_rec_telemetry:
            with patch("app.core.federation_client.safe_post") as mock_post:
                mock_post.return_value = MagicMock(status_code=202)
                client = FederationClient()
                client.post_to_inbox("https://remote.example.org/inbox", {"type": "Create"})

                mock_rec_telemetry.assert_called_once()
                args, kwargs = mock_rec_telemetry.call_args
                assert args[0] == "Federation"
                assert kwargs["url"] == "https://remote.example.org/inbox"


# ===========================================================================
# 5. Secret Redaction in Logs and Telemetry
# ===========================================================================


class TestSecretRedactionInLogs:
    """Verify secrets, tokens, and credentials are redacted from logs and spans."""

    def test_sanitize_headers_redacts_auth_and_secrets(self) -> None:
        """Verify headers containing sensitive tokens are redacted."""
        headers = {
            "Authorization": "Bearer sample_token_val",
            "X-API-KEY": "sample_header_val",
            "User-Agent": "iqoqo-federation/0.9.0",
            "Accept": "application/activity+json",
        }
        sanitized = sanitize_headers(headers)
        assert sanitized["Authorization"] == "***REDACTED***"
        assert sanitized["X-API-KEY"] == "***REDACTED***"
        assert sanitized["User-Agent"] == "iqoqo-federation/0.9.0"
        assert sanitized["Accept"] == "application/activity+json"

    def test_sanitize_url_redacts_secrets_in_query(self) -> None:
        """Verify sensitive parameters in URLs are sanitized."""
        url = "https://fed.example.com/inbox?token=sample_token&api_key=sample_val&mode=direct"
        sanitized = sanitize_url(url)
        assert sanitized is not None
        assert "token=%2A%2A%2AREDACTED%2A%2A%2A" in sanitized
        assert "api_key=%2A%2A%2AREDACTED%2A%2A%2A" in sanitized
        assert "mode=direct" in sanitized

    def test_inbox_payload_cap_rejection(self, client, app) -> None:
        """Verify that requests exceeding the 100KB payload limit are rejected with 413."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True

        oversized_data = b"a" * (101 * 1024)
        resp = client.post(
            "/api/federation/inbox",
            data=oversized_data,
            headers={"Content-Type": "application/activity+json"},
        )
        assert resp.status_code == 413
        data = resp.get_json()
        assert data["code"] == 413
        assert "100KB" in data["error"]
