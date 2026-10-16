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
"""Tests for HTTP Signatures draft-cavage-12 signing and verification."""

from __future__ import annotations

import email.utils
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.http_signatures import (
    DateSkewError,
    DigestMismatchError,
    SignatureVerificationError,
    compute_digest,
    sign_request,
    verify_request,
)


class MockRequest:
    """Mock Flask-like request object for signature verification testing."""

    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes = b"",
        query_string: str = "",
    ):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query_string = query_string

    def get_data(self) -> bytes:
        return self.body


@pytest.fixture
def rsa_keypair():
    """Generate ephemeral RSA-2048 keypair for testing."""
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


class TestHttpSignatures:
    """Test suite for draft-cavage-12 HTTP message signing and verification."""

    def test_compute_digest(self):
        body = b'{"type":"Person","name":"Alice"}'
        digest = compute_digest(body)
        assert digest.startswith("SHA-256=")

        # Deterministic check
        assert compute_digest(body) == digest
        assert compute_digest(None) == compute_digest(b"")

    def test_sign_and_verify_valid_request(self, rsa_keypair):
        priv_key, pub_pem = rsa_keypair
        actor_uri = "https://example.org/users/alice"
        key_id = f"{actor_uri}#main-key"
        body = b'{"type":"Note","content":"Hello world"}'

        signed_headers = sign_request(
            method="POST",
            url=f"{actor_uri}/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        assert "Signature" in signed_headers
        assert "Digest" in signed_headers
        assert "Date" in signed_headers
        assert "Host" in signed_headers
        assert signed_headers["Host"] == "example.org"

        req = MockRequest(
            method="POST",
            path="/users/alice/inbox",
            headers=signed_headers,
            body=body,
        )

        verified_actor = verify_request(req, key_resolver=lambda _: pub_pem)
        assert verified_actor == actor_uri

    def test_verify_date_skew_rejected(self, rsa_keypair):
        priv_key, pub_pem = rsa_keypair
        actor_uri = "https://example.org/users/alice"
        key_id = f"{actor_uri}#main-key"
        body = b"{}"

        signed_headers = sign_request(
            method="POST",
            url=f"{actor_uri}/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        # Skew Date by 350 seconds into past
        skewed_time = datetime.now(UTC) - timedelta(seconds=350)
        signed_headers["Date"] = email.utils.formatdate(skewed_time.timestamp(), usegmt=True)

        req = MockRequest(
            method="POST",
            path="/users/alice/inbox",
            headers=signed_headers,
            body=body,
        )

        with pytest.raises(DateSkewError):
            verify_request(req, max_skew_seconds=300, key_resolver=lambda _: pub_pem)

    def test_verify_digest_mismatch_rejected(self, rsa_keypair):
        priv_key, pub_pem = rsa_keypair
        actor_uri = "https://example.org/users/alice"
        key_id = f"{actor_uri}#main-key"
        body = b'{"type":"Like"}'

        signed_headers = sign_request(
            method="POST",
            url=f"{actor_uri}/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        # Tamper body after signing
        tampered_body = b'{"type":"Dislike"}'
        req = MockRequest(
            method="POST",
            path="/users/alice/inbox",
            headers=signed_headers,
            body=tampered_body,
        )

        with pytest.raises(DigestMismatchError):
            verify_request(req, key_resolver=lambda _: pub_pem)

    def test_verify_domain_mismatch_rejected(self, rsa_keypair):
        priv_key, pub_pem = rsa_keypair
        # Attacker on evil.com tries to authenticate activity claimed by victim.com
        key_id = "https://evil.com/actor#main-key"
        body = b'{"type":"Create","actor":"https://victim.com/users/alice"}'

        signed_headers = sign_request(
            method="POST",
            url="https://target.com/inbox",
            body=body,
            key_id=key_id,
            private_key=priv_key,
        )

        req = MockRequest(
            method="POST",
            path="/inbox",
            headers=signed_headers,
            body=body,
        )

        # Mismatch between payload actor domain (victim.com) and keyId (evil.com)
        with pytest.raises(SignatureVerificationError):
            verify_request(req, key_resolver=lambda _: pub_pem)

        # Also test expected_actor_uri mismatch
        with pytest.raises(SignatureVerificationError):
            verify_request(req, key_resolver=lambda _: pub_pem, expected_actor_uri="https://victim.com/users/alice")

    def test_missing_signature_header_rejected(self):
        req = MockRequest(method="GET", path="/actor", headers={})
        with pytest.raises(SignatureVerificationError):
            verify_request(req)
