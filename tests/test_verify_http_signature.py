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

"""Tests for scripts/verify_http_signature.py CLI and helper functions."""

import base64
import hashlib
import time
from email.utils import formatdate
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from scripts.verify_http_signature import (
    main,
    parse_signature_header,
    verify_date_skew,
    verify_digest,
    verify_rsa_signature,
)


@pytest.fixture
def rsa_keypair():
    """Generate ephemeral RSA keypair for signature tests."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {
        "private_key": private_key,
        "private_pem": private_pem,
        "public_pem": public_pem,
    }


def test_parse_signature_header():
    """Verify parsing key=value pairs out of HTTP Signature header."""
    header = (
        'keyId="https://example.com/actor#main-key",algorithm="rsa-sha256",'
        'headers="(request-target) host date digest",signature="mock_sig_123="'
    )
    parsed = parse_signature_header(header)
    assert parsed["keyId"] == "https://example.com/actor#main-key"
    assert parsed["algorithm"] == "rsa-sha256"
    assert parsed["headers"] == "(request-target) host date digest"
    assert parsed["signature"] == "mock_sig_123="


def test_parse_signature_header_empty():
    """Verify parsing malformed or empty signature header returns empty dict."""
    assert parse_signature_header("") == {}
    assert parse_signature_header("invalid format") == {}


def test_verify_digest():
    """Verify SHA-256 Digest header calculation and validation."""
    body = b'{"type":"Follow","actor":"https://example.com/actor"}'
    expected_b64 = base64.b64encode(hashlib.sha256(body).digest()).decode("utf-8")
    valid_header = f"SHA-256={expected_b64}"

    assert verify_digest(body, valid_header) is True
    assert verify_digest(body, "SHA-256=invalidDigest") is False
    assert verify_digest(body, f"MD5={expected_b64}") is False
    assert verify_digest(body, "") is False


def test_verify_date_skew():
    """Verify Date header clock skew checking within 300s window."""
    now_date = formatdate(time.time(), usegmt=True)
    assert verify_date_skew(now_date, max_skew_seconds=300) is True

    skewed_past = formatdate(time.time() - 600, usegmt=True)
    assert verify_date_skew(skewed_past, max_skew_seconds=300) is False

    skewed_future = formatdate(time.time() + 600, usegmt=True)
    assert verify_date_skew(skewed_future, max_skew_seconds=300) is False

    assert verify_date_skew("not-a-date") is False


def test_verify_rsa_signature(rsa_keypair):
    """Verify RSA-SHA256 signature verification with valid and corrupted inputs."""
    priv = rsa_keypair["private_key"]
    pub_pem = rsa_keypair["public_pem"]
    signing_string = "(request-target): post /inbox\nhost: localhost\ndate: Mon, 01 Jan 2026 00:00:00 GMT"

    sig_bytes = priv.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

    assert verify_rsa_signature(pub_pem, signing_string, sig_b64) is True

    # Tampered signing string
    assert verify_rsa_signature(pub_pem, signing_string + "\nextra: 1", sig_b64) is False

    # Tampered signature
    tampered_sig = base64.b64encode(sig_bytes[:-4] + b"dead").decode("utf-8")
    assert verify_rsa_signature(pub_pem, signing_string, tampered_sig) is False

    # Corrupted key
    assert verify_rsa_signature(b"invalid-pem", signing_string, sig_b64) is False


def test_main_success_flow(rsa_keypair, tmp_path):
    """Verify main CLI success exit code 0 when signature, date, and digest match."""
    priv = rsa_keypair["private_key"]
    pub_pem = rsa_keypair["public_pem"]

    key_file = tmp_path / "pubkey.pem"
    key_file.write_bytes(pub_pem)

    body = '{"type":"Follow","actor":"https://peer.example/u/alice"}'
    body_bytes = body.encode("utf-8")
    digest_val = "SHA-256=" + base64.b64encode(hashlib.sha256(body_bytes).digest()).decode("utf-8")
    date_val = formatdate(time.time(), usegmt=True)

    signing_string = f"(request-target): post /inbox\n" f"host: localhost\n" f"date: {date_val}\n" f"digest: {digest_val}"
    sig_bytes = priv.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

    sig_header = (
        f'keyId="https://peer.example/u/alice#main-key",algorithm="rsa-sha256",'
        f'headers="(request-target) host date digest",signature="{sig_b64}"'
    )

    args = [
        "verify_http_signature.py",
        "--signature",
        sig_header,
        "--public-key",
        str(key_file),
        "--method",
        "POST",
        "--path",
        "/inbox",
        "--host",
        "localhost",
        "--date",
        date_val,
        "--digest",
        digest_val,
        "--body",
        body,
    ]

    with patch("sys.argv", args):
        assert main() == 0


def test_main_missing_signature_fields(tmp_path):
    """Verify main CLI returns 1 on incomplete Signature header."""
    args = [
        "verify_http_signature.py",
        "--signature",
        'keyId="https://peer.example/actor"',
        "--public-key",
        str(tmp_path / "dummy.pem"),
    ]
    with patch("sys.argv", args):
        assert main() == 1


def test_main_date_skew_failure(rsa_keypair, tmp_path):
    """Verify main CLI returns 2 when Date is outside skew window."""
    pub_file = tmp_path / "pubkey.pem"
    pub_file.write_bytes(rsa_keypair["public_pem"])

    stale_date = formatdate(time.time() - 1000, usegmt=True)
    sig_header = 'keyId="key1",headers="date",signature="dummy="'

    args = [
        "verify_http_signature.py",
        "--signature",
        sig_header,
        "--public-key",
        str(pub_file),
        "--date",
        stale_date,
    ]
    with patch("sys.argv", args):
        assert main() == 2


def test_main_digest_mismatch_failure(rsa_keypair, tmp_path):
    """Verify main CLI returns 3 when body doesn't match Digest header."""
    pub_file = tmp_path / "pubkey.pem"
    pub_file.write_bytes(rsa_keypair["public_pem"])

    date_val = formatdate(time.time(), usegmt=True)
    sig_header = 'keyId="key1",headers="digest",signature="dummy="'

    args = [
        "verify_http_signature.py",
        "--signature",
        sig_header,
        "--public-key",
        str(pub_file),
        "--date",
        date_val,
        "--body",
        "hello",
        "--digest",
        "SHA-256=invalidDigestBase64=",
    ]
    with patch("sys.argv", args):
        assert main() == 3


def test_main_missing_signed_header_failure(rsa_keypair, tmp_path):
    """Verify main CLI returns 4 when a signed header is not supplied in args."""
    pub_file = tmp_path / "pubkey.pem"
    pub_file.write_bytes(rsa_keypair["public_pem"])

    date_val = formatdate(time.time(), usegmt=True)
    sig_header = 'keyId="key1",headers="(request-target) missing-header",signature="dummy="'

    args = [
        "verify_http_signature.py",
        "--signature",
        sig_header,
        "--public-key",
        str(pub_file),
        "--date",
        date_val,
    ]
    with patch("sys.argv", args):
        assert main() == 4
