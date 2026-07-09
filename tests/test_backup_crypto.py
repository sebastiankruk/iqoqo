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
"""Tests for the joserfc backup manifest signing strategy.

Validates that backup manifests are correctly encoded and decoded using the
modern joserfc implementation, proving migration off the deprecated authlib.jose
path and ensuring archive authenticity verification works end-to-end.
"""

import base64
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from joserfc import jwt as jose_jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey

from scripts.backup import _b64url_encode, create_export, generate_backup_manifest_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRET = "iqoqo-secure-test-key-for-backups-phase5"
WRONG_SECRET = "completely-wrong-key-should-not-decode"


def _make_key(secret: str) -> OctKey:
    """Return a joserfc OctKey from a plain secret string."""
    return OctKey.import_key({"use": "sig", "kty": "oct", "k": _b64url_encode(secret)})


# ---------------------------------------------------------------------------
# Unit tests: _b64url_encode
# ---------------------------------------------------------------------------


def test_b64url_encode_produces_valid_base64url():
    """Encoded string must be valid base64url without padding."""
    result = _b64url_encode("hello")
    # Must not contain padding '=' or standard b64 chars '+' or '/'
    assert "=" not in result
    assert "+" not in result
    assert "/" not in result
    # Must be decodable back to original
    padded = result + "=" * (4 - len(result) % 4)
    decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
    assert decoded == "hello"


def test_b64url_encode_non_ascii_characters():
    """Encoder must handle unicode content without crashing."""
    result = _b64url_encode("ąęśćżźóń-unicode")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Unit tests: generate_backup_manifest_token
# ---------------------------------------------------------------------------


def test_backup_manifest_token_is_compact_jwt():
    """Token must be a 3-part compact-serialised JWT."""
    payload = {"timestamp": "20260709_120000", "version": "0.7.8", "type": "full_archive"}
    token = generate_backup_manifest_token(payload, SECRET)
    parts = token.split(".")
    assert len(parts) == 3, f"Expected 3 JWT parts, got {len(parts)}: {token}"


def test_backup_manifest_token_header_uses_hs256():
    """JWT header must declare alg=HS256."""
    payload = {"v": "test"}
    token = generate_backup_manifest_token(payload, SECRET)
    header_part = token.split(".")[0]
    # Pad and decode
    padded = header_part + "=" * (4 - len(header_part) % 4)
    header = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    assert header.get("alg") == "HS256"


def test_backup_manifest_token_decodes_correctly():
    """All claims from the original payload must survive encode/decode round-trip."""
    payload = {
        "timestamp": "20260709_120000",
        "version": "0.7.8",
        "type": "full_archive",
        "iss": "iqoqo-backup",
        "entities_count": 1337,
    }
    token = generate_backup_manifest_token(payload, SECRET)
    key = _make_key(SECRET)
    decoded = jose_jwt.decode(token, key)
    for claim_key, claim_val in payload.items():
        assert decoded.claims[claim_key] == claim_val, f"Claim '{claim_key}' mismatch"


def test_backup_manifest_fails_with_wrong_key():
    """Decoding with a wrong key must raise JoseError — not silently succeed."""
    payload = {"data": "sensitive_backup_info", "version": "0.7.8"}
    token = generate_backup_manifest_token(payload, SECRET)
    wrong_key = _make_key(WRONG_SECRET)
    with pytest.raises(JoseError):
        jose_jwt.decode(token, wrong_key)


def test_backup_manifest_token_is_string():
    """Token must be a non-empty string regardless of payload size."""
    token = generate_backup_manifest_token({}, SECRET)
    assert isinstance(token, str)
    assert len(token) > 0


def test_backup_manifest_different_secrets_produce_different_tokens():
    """Two different signing keys must produce two different tokens."""
    payload = {"version": "0.7.8"}
    token_a = generate_backup_manifest_token(payload, SECRET)
    token_b = generate_backup_manifest_token(payload, WRONG_SECRET)
    # Signature parts must differ
    assert token_a.split(".")[2] != token_b.split(".")[2]


# ---------------------------------------------------------------------------
# Integration test: create_export produces manifest.jwt in the zip
# ---------------------------------------------------------------------------


def test_create_export_includes_manifest_jwt(app, tmp_path):
    """create_export() must produce a zip containing both metadata.json and manifest.jwt."""
    covers_dir = tmp_path / "app" / "static" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch.dict("os.environ", {"BACKUP_DIR": str(tmp_path)}),
        patch("app.config.Config.BASE_DIR", str(tmp_path)),
        patch("app.core.data_manager.DataManager.export_all") as mock_export,
    ):
        mock_export.return_value = {"test": "data"}
        app.config["BACKUP_DIR"] = str(tmp_path)

        create_export(app=app)

        zips = list(tmp_path.glob("*.zip"))
        assert len(zips) == 1, f"Expected exactly one zip, found: {zips}"

        with zipfile.ZipFile(zips[0], "r") as zf:
            names = zf.namelist()
            assert "metadata.json" in names, f"metadata.json missing from zip; found: {names}"
            assert "manifest.jwt" in names, f"manifest.jwt missing from zip; found: {names}"

            # The manifest token must be a valid 3-part JWT
            jwt_content = zf.read("manifest.jwt").decode("utf-8").strip()
            assert len(jwt_content.split(".")) == 3, f"manifest.jwt is not a valid JWT: {jwt_content}"


def test_create_export_manifest_jwt_has_correct_claims(app, tmp_path):
    """manifest.jwt inside the backup zip must decode to valid iqoqo claims."""
    covers_dir = tmp_path / "app" / "static" / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    secret = "test-secret-for-claims-check"
    with (
        patch.dict("os.environ", {"BACKUP_DIR": str(tmp_path), "IQOQO_SECRET_KEY": secret}),
        patch("app.config.Config.BASE_DIR", str(tmp_path)),
        patch("app.core.data_manager.DataManager.export_all", return_value={}),
    ):
        app.config["BACKUP_DIR"] = str(tmp_path)
        app.config["SECRET_KEY"] = secret

        create_export(app=app)

        zips = list(tmp_path.glob("*.zip"))
        assert zips, "No zip produced"

        with zipfile.ZipFile(zips[0], "r") as zf:
            jwt_content = zf.read("manifest.jwt").decode("utf-8").strip()

        key = _make_key(secret)
        decoded = jose_jwt.decode(jwt_content, key)
        assert decoded.claims["iss"] == "iqoqo-backup"
        assert decoded.claims["type"] == "full_archive"
        assert "timestamp" in decoded.claims
