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
"""HTTP Signatures signing and verification (draft-cavage-http-signatures-12)."""

from __future__ import annotations

import base64
import email.utils
import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class SignatureError(Exception):
    """Base error for HTTP Signature operations."""


class SignatureVerificationError(SignatureError):
    """Raised when signature verification fails."""


class DateSkewError(SignatureVerificationError):
    """Raised when Date header skew exceeds the allowed threshold."""


class DigestMismatchError(SignatureVerificationError):
    """Raised when SHA-256 Digest header does not match body payload."""


class KeyFetchError(SignatureVerificationError):
    """Raised when public key could not be retrieved or resolved."""


def compute_digest(body: bytes | str | None) -> str:
    """Compute RFC 3230 SHA-256 Digest header value for a request body.

    Args:
        body: Request payload bytes or string.

    Returns:
        Formatted digest string like 'SHA-256=<base64-sha256>'.
    """
    if body is None:
        raw_bytes = b""
    elif isinstance(body, str):
        raw_bytes = body.encode("utf-8")
    else:
        raw_bytes = body

    digest_b64 = base64.b64encode(hashlib.sha256(raw_bytes).digest()).decode("ascii")
    return f"SHA-256={digest_b64}"


def sign_request(
    method: str,
    url: str,
    body: bytes | str | None,
    key_id: str,
    private_key: rsa.RSAPrivateKey | bytes | str,
    headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Sign an outbound HTTP request using draft-cavage-http-signatures-12.

    Signs (request-target), host, date, and digest headers.

    Args:
        method: HTTP method (e.g. GET, POST).
        url: Full target URL.
        body: Request payload.
        key_id: Public key URI identifying the signer key.
        private_key: RSA private key instance or PEM string/bytes.
        headers: Optional base headers to augment and return.

    Returns:
        Updated dictionary containing signed headers: Host, Date, Digest, Signature.
    """
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    date_str = email.utils.formatdate(usegmt=True)
    out_headers = dict(headers or {})
    out_headers["Host"] = host
    out_headers["Date"] = date_str

    is_bodyless = body is None and method.upper() in {"GET", "HEAD", "DELETE"}
    if is_bodyless:
        headers_to_sign = "(request-target) host date"
        signing_string = f"(request-target): {method.lower()} {path}\n" f"host: {host}\n" f"date: {date_str}"
    else:
        digest_val = compute_digest(body)
        out_headers["Digest"] = digest_val
        headers_to_sign = "(request-target) host date digest"
        signing_string = f"(request-target): {method.lower()} {path}\n" f"host: {host}\n" f"date: {date_str}\n" f"digest: {digest_val}"

    # Ensure private key is RSAPrivateKey instance
    if isinstance(private_key, (bytes, str)):
        raw_pem = private_key.encode("utf-8") if isinstance(private_key, str) else private_key
        priv_key_obj = serialization.load_pem_private_key(raw_pem, password=None)
    else:
        priv_key_obj = private_key

    if not isinstance(priv_key_obj, rsa.RSAPrivateKey):
        raise SignatureError("Expected an RSA private key for signing")

    sig_bytes = priv_key_obj.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    sig_header = f'keyId="{key_id}",' f'algorithm="rsa-sha256",' f'headers="{headers_to_sign}",' f'signature="{sig_b64}"'
    out_headers["Signature"] = sig_header

    return out_headers


_SIG_PARAM_RE = re.compile(r'([a-zA-Z]+)="([^"]*)"')


def _parse_signature_header(header_value: str) -> dict[str, str]:
    """Parse keyId, algorithm, headers, and signature parameters from header."""
    header_val = header_value.strip()
    if header_val.startswith("Signature "):
        header_val = header_val[10:].strip()

    matches = _SIG_PARAM_RE.findall(header_val)
    return dict(matches)


def _get_header(request: Any, header_name: str) -> str:
    """Retrieve header value case-insensitively from request or dictionary."""
    headers = getattr(request, "headers", None)
    if headers is None:
        return ""
    if hasattr(headers, "get"):
        val = headers.get(header_name)
        if val is not None:
            return str(val)
        if hasattr(headers, "items"):
            target = header_name.lower()
            for k, v in headers.items():
                if str(k).lower() == target:
                    return str(v)
    return ""


def _record_sig_failure(reason: str) -> None:
    """Record HTTP signature verification failure metric."""
    try:
        from app.core.telemetry import federation_sig_failures_total

        federation_sig_failures_total.add(1, {"reason": reason})
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, ImportError):
        pass


def verify_request(
    request: Any,
    max_skew_seconds: int = 300,
    key_resolver: Callable[[str], str | None] | None = None,
    expected_actor_uri: str | None = None,
) -> str:
    """Verify draft-cavage-12 HTTP Signature on an incoming request.

    Enforces +/-300s Date skew validation, SHA-256 Digest header checks,
    and actor vs. keyId domain matching.

    Args:
        request: Flask request or request-like object.
        max_skew_seconds: Maximum permitted Date header skew in seconds (default: 300).
        key_resolver: Optional callable (key_id: str) -> public_key_pem.
        expected_actor_uri: Optional expected actor URI for explicit identity checking.

    Returns:
        Verified actor URI string.

    Raises:
        SignatureVerificationError: If verification fails.
        DateSkewError: If Date skew exceeds permitted threshold.
        DigestMismatchError: If Digest header doesn't match body.
        KeyFetchError: If public key cannot be resolved.
    """
    # 1. Parse Signature header
    sig_raw = _get_header(request, "Signature") or _get_header(request, "Authorization")
    if not sig_raw:
        _record_sig_failure("missing_signature_header")
        raise SignatureVerificationError("Missing Signature header")

    params = _parse_signature_header(sig_raw)
    key_id = params.get("keyId")
    sig_b64 = params.get("signature")
    algorithm = params.get("algorithm", "rsa-sha256")
    headers_str = params.get("headers", "(request-target)")

    if not key_id or not sig_b64:
        _record_sig_failure("missing_params")
        raise SignatureVerificationError("Signature header missing keyId or signature")

    if algorithm.lower() not in ("rsa-sha256", "hs2019"):
        _record_sig_failure("unsupported_algorithm")
        raise SignatureVerificationError(f"Unsupported signature algorithm: {algorithm}")

    headers_list = [h.strip().lower() for h in headers_str.split(" ") if h.strip()]

    # Enforcement: mandatory signed headers (draft-cavage-12)
    body_bytes = request.get_data() if hasattr(request, "get_data") else getattr(request, "body", b"")
    if isinstance(body_bytes, str):
        body_bytes = body_bytes.encode("utf-8")

    required_headers = {"(request-target)", "host", "date"}
    if body_bytes:
        required_headers.add("digest")

    missing_signed = required_headers - set(headers_list)
    if missing_signed:
        _record_sig_failure("missing_mandatory_signed_headers")
        raise SignatureVerificationError(f"Signature header must sign mandatory headers: {', '.join(sorted(missing_signed))}")

    # 2. Date skew validation (+/- 300s)
    date_str = _get_header(request, "Date")
    if not date_str:
        _record_sig_failure("missing_date_header")
        raise DateSkewError("Missing Date header in signed request")

    try:
        date_dt = email.utils.parsedate_to_datetime(date_str)
        if date_dt.tzinfo is None:
            date_dt = date_dt.replace(tzinfo=UTC)
    except Exception as exc:
        _record_sig_failure("invalid_date_format")
        raise DateSkewError(f"Invalid Date header format: {date_str}") from exc

    now = datetime.now(UTC)
    skew = abs((now - date_dt).total_seconds())
    if skew > max_skew_seconds:
        _record_sig_failure("date_skew_exceeded")
        raise DateSkewError(f"Date header skew ({skew:.1f}s) exceeds maximum allowed ({max_skew_seconds}s)")

    # 3. Digest header verification
    if "digest" in headers_list or _get_header(request, "Digest"):
        digest_hdr = _get_header(request, "Digest")
        if not digest_hdr:
            _record_sig_failure("missing_digest_header")
            raise DigestMismatchError("Missing Digest header in request")

        expected_digest = compute_digest(body_bytes)
        if digest_hdr.strip() != expected_digest:
            _record_sig_failure("digest_mismatch")
            raise DigestMismatchError(f"Digest header mismatch: expected {expected_digest}, got {digest_hdr}")

    # 4. Actor vs keyId domain matching and exact actor verification
    actor_uri = key_id.split("#")[0]
    key_netloc = urlparse(key_id).netloc.lower()
    actor_netloc = urlparse(actor_uri).netloc.lower()

    if not key_netloc or not actor_netloc or key_netloc != actor_netloc:
        _record_sig_failure("domain_mismatch")
        raise SignatureVerificationError(f"keyId domain ({key_netloc}) does not match actor domain ({actor_netloc})")

    if expected_actor_uri:
        exp_netloc = urlparse(expected_actor_uri).netloc.lower()
        if exp_netloc and exp_netloc != key_netloc:
            _record_sig_failure("domain_mismatch")
            raise SignatureVerificationError(f"keyId domain ({key_netloc}) does not match expected actor domain ({exp_netloc})")
        if expected_actor_uri != actor_uri:
            _record_sig_failure("actor_mismatch")
            raise SignatureVerificationError(f"keyId actor ({actor_uri}) does not match expected actor ({expected_actor_uri})")

    if body_bytes:
        try:
            body_json = json.loads(body_bytes.decode("utf-8"))
            if isinstance(body_json, dict) and "actor" in body_json:
                payload_actor_raw = body_json["actor"]
                payload_actor = payload_actor_raw.get("id") if isinstance(payload_actor_raw, dict) else payload_actor_raw
                if isinstance(payload_actor, str) and payload_actor:
                    p_netloc = urlparse(payload_actor).netloc.lower()
                    if p_netloc and p_netloc != key_netloc:
                        _record_sig_failure("domain_mismatch")
                        raise SignatureVerificationError(f"keyId domain ({key_netloc}) does not match payload actor domain ({p_netloc})")
                    if payload_actor != actor_uri:
                        _record_sig_failure("actor_impersonation")
                        raise SignatureVerificationError(f"Signing key actor ({actor_uri}) does not match payload actor ({payload_actor})")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # 5. Resolve public key
    public_key_pem: str | None = None
    if key_resolver:
        public_key_pem = key_resolver(key_id)

    if not public_key_pem:
        # Check local database cache
        try:
            from app.db import db
            from app.db.federation import FederationActor

            actor_record = db.session.execute(db.select(FederationActor).where(FederationActor.actor_uri == actor_uri)).scalars().first()
            if actor_record and actor_record.public_key_pem:
                public_key_pem = actor_record.public_key_pem
        except Exception:
            pass

    if not public_key_pem:
        # Fetch remote actor via FederationClient
        try:
            from app.core.federation_client import FederationClient

            client = FederationClient()
            actor_data = client.fetch_actor(actor_uri)
            if actor_data and "publicKey" in actor_data:
                pk_info = actor_data["publicKey"]
                if isinstance(pk_info, dict) and "publicKeyPem" in pk_info:
                    public_key_pem = pk_info["publicKeyPem"]
        except Exception as exc:
            _record_sig_failure("key_fetch_error")
            raise KeyFetchError(f"Failed to fetch public key for actor {actor_uri}: {exc}") from exc

    if not public_key_pem:
        _record_sig_failure("key_not_resolved")
        raise KeyFetchError(f"Could not resolve public key for keyId {key_id}")

    # 6. Reconstruct signing string
    lines: list[str] = []
    for h in headers_list:
        if h == "(request-target)":
            method = request.method.lower()
            path = request.path
            if hasattr(request, "query_string") and request.query_string:
                qs = request.query_string.decode("utf-8") if isinstance(request.query_string, bytes) else str(request.query_string)
                if qs:
                    path = f"{path}?{qs}"
            lines.append(f"(request-target): {method} {path}")
        elif h == "host":
            h_val = _get_header(request, "Host") or getattr(request, "host", "")
            lines.append(f"host: {h_val}")
        else:
            h_val = _get_header(request, h)
            lines.append(f"{h}: {h_val}")

    signing_string = "\n".join(lines)

    # 7. Cryptographic signature verification
    try:
        pub_key_obj = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        sig_bytes = base64.b64decode(sig_b64)
        pub_key_obj.verify(  # type: ignore[union-attr]
            sig_bytes,
            signing_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as exc:
        # Re-fetch actor's remote JSON-LD document and retry verification once
        # to handle remote key rotation without dropouts (enforcing 60s cooldown)
        refreshed_pem: str | None = None
        should_refetch = True

        try:
            from app.db import db
            from app.db.federation import FederationActor

            actor_rec = db.session.execute(db.select(FederationActor).where(FederationActor.actor_uri == actor_uri)).scalars().first()
            if actor_rec and actor_rec.last_fetched_at:
                age_seconds = (
                    datetime.now(UTC) - actor_rec.last_fetched_at.replace(tzinfo=UTC if actor_rec.last_fetched_at.tzinfo is None else None)
                ).total_seconds()
                if age_seconds < 60:
                    should_refetch = False
        except Exception:
            actor_rec = None
            should_refetch = True

        if should_refetch:
            try:
                from app.core.federation_client import FederationClient

                client = FederationClient()
                actor_data = client.fetch_actor(actor_uri)
                if actor_data and "publicKey" in actor_data:
                    pk_info = actor_data["publicKey"]
                    if isinstance(pk_info, dict) and "publicKeyPem" in pk_info:
                        refreshed_pem = pk_info["publicKeyPem"]
            except Exception:
                refreshed_pem = None

        if refreshed_pem and refreshed_pem != public_key_pem:
            try:
                new_pub_key_obj = serialization.load_pem_public_key(refreshed_pem.encode("utf-8"))
                new_pub_key_obj.verify(  # type: ignore[union-attr]
                    sig_bytes,
                    signing_string.encode("utf-8"),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                # Persist updated rotated key back to database
                try:
                    from app.db import db
                    from app.db.federation import FederationActor

                    if not actor_rec:
                        actor_rec = (
                            db.session.execute(db.select(FederationActor).where(FederationActor.actor_uri == actor_uri)).scalars().first()
                        )
                    if actor_rec:
                        actor_rec.public_key_pem = refreshed_pem
                        actor_rec.last_fetched_at = datetime.now(UTC)
                        db.session.commit()
                except Exception:
                    pass

                return actor_uri
            except Exception:
                pass

        _record_sig_failure("crypto_verification_failed")
        raise SignatureVerificationError(f"RSA signature verification failed: {exc}") from exc

    return actor_uri
