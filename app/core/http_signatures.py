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
"""HTTP Signatures for ActivityPub S2S authentication.

Implements draft-cavage-http-signatures-12 for Mastodon-compatible
server-to-server communication.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re
from datetime import UTC, datetime
from email.utils import formatdate
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)


class SignatureVerificationError(Exception):
    """Raised when HTTP signature verification fails."""


def _digest_body(body: bytes) -> str:
    """Compute SHA-256 digest of request body."""
    digest = hashlib.sha256(body).digest()
    return f"SHA-256={base64.b64encode(digest).decode('ascii')}"


def sign_request(
    method: str,
    url: str,
    body: bytes | None,
    actor_key_id: str,
    private_key: rsa.RSAPrivateKey,
    additional_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Sign an HTTP request using draft-cavage-http-signatures-12.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full URL of the request target.
        body: Request body bytes (for POST/PUT).
        actor_key_id: Full key ID URI (e.g., https://instance/actor/user#main-key).
        private_key: RSA private key for signing.
        additional_headers: Extra headers to include in the signature.

    Returns:
        Dict of headers to add to the request (Signature, Date, Digest, Host).
    """
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.port and parsed.port not in (80, 443):
        host = f"{parsed.hostname}:{parsed.port}"

    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    now = datetime.now(UTC)
    date_str = formatdate(timeval=now.timestamp(), localtime=False, usegmt=True)

    headers: dict[str, str] = {
        "Host": host or "",
        "Date": date_str,
    }

    if additional_headers:
        headers.update(additional_headers)

    # Signed headers list
    signed_headers = ["(request-target)", "host", "date"]

    if body:
        digest = _digest_body(body)
        headers["Digest"] = digest
        signed_headers.append("digest")

    # Build signing string
    signing_parts = []
    lower_headers: dict[str, str] = {k.lower(): v for k, v in headers.items()}
    for header in signed_headers:
        if header == "(request-target)":
            signing_parts.append(f"(request-target): {method.lower()} {path}")
        else:
            signing_parts.append(f"{header}: {lower_headers[header]}")

    signing_string = "\n".join(signing_parts)

    # Sign with RSA-SHA256
    signature_bytes = private_key.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

    # Build Signature header
    sig_header = f'keyId="{actor_key_id}",algorithm="rsa-sha256",headers="{" ".join(signed_headers)}",signature="{signature_b64}"'

    headers["Signature"] = sig_header
    return headers


def _parse_signature_header(sig_header: str) -> dict[str, str]:
    """Parse a Signature header value into its components."""
    result: dict[str, str] = {}
    # Match key="value" pairs
    pattern = r'(\w+)="([^"]*)"'
    for match in re.finditer(pattern, sig_header):
        result[match.group(1)] = match.group(2)
    return result


def verify_request(
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes | None,
    public_key_pem: str,
) -> str:
    """Verify an HTTP signature on an incoming request.

    Args:
        method: HTTP method of the request.
        path: Request path (including query string).
        headers: Request headers dict (case-insensitive keys).
        body: Request body bytes.
        public_key_pem: PEM-encoded public key of the remote actor.

    Returns:
        The keyId from the signature (for actor identification).

    Raises:
        SignatureVerificationError: If verification fails.
    """
    # Normalize header keys to lowercase for lookup
    lower_headers: dict[str, str] = {k.lower(): v for k, v in headers.items()}

    sig_header = lower_headers.get("signature")
    if not sig_header:
        raise SignatureVerificationError("Missing Signature header")

    sig_parts = _parse_signature_header(sig_header)
    key_id = sig_parts.get("keyId")
    algorithm = sig_parts.get("algorithm", "rsa-sha256")
    signed_headers_str = sig_parts.get("headers", "date")
    signature_b64 = sig_parts.get("signature")

    if not key_id or not signature_b64:
        raise SignatureVerificationError("Incomplete Signature header")

    if algorithm != "rsa-sha256":
        raise SignatureVerificationError(f"Unsupported algorithm: {algorithm}")

    # Verify digest if present
    if body and "digest" in signed_headers_str:
        expected_digest = _digest_body(body)
        actual_digest = lower_headers.get("digest", "")
        if expected_digest != actual_digest:
            raise SignatureVerificationError("Digest mismatch")

    # Reconstruct signing string
    signed_headers = signed_headers_str.split(" ")
    signing_parts = []
    for header in signed_headers:
        if header == "(request-target)":
            signing_parts.append(f"(request-target): {method.lower()} {path}")
        else:
            value = lower_headers.get(header, "")
            signing_parts.append(f"{header}: {value}")

    signing_string = "\n".join(signing_parts)

    # Load public key and verify
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise SignatureVerificationError(f"Invalid public key: {exc}") from exc

    try:
        signature_bytes = base64.b64decode(signature_b64)
        public_key.verify(  # type: ignore[union-attr, call-arg]
            signature_bytes,
            signing_string.encode("utf-8"),
            padding.PKCS1v15(),  # type: ignore[arg-type]
            hashes.SHA256(),  # type: ignore[arg-type]
        )
    except Exception as exc:
        raise SignatureVerificationError(f"Signature verification failed: {exc}") from exc

    return key_id


def verify_flask_request(request: Any) -> str:
    """Convenience wrapper to verify a Flask request object.

    Args:
        request: Flask request object.

    Returns:
        The keyId URI from the verified signature.

    Raises:
        SignatureVerificationError: If verification fails or actor cannot be resolved.
    """
    from app.db.federation import FederationActor

    headers = dict(request.headers)
    body = request.get_data()
    method = request.method
    path = request.full_path if request.query_string else request.path

    # Validate Date header freshness (±5 minutes) to prevent replay attacks
    date_header = headers.get("Date")
    if date_header:
        from email.utils import parsedate_to_datetime

        try:
            request_date = parsedate_to_datetime(date_header)
            now = datetime.now(UTC)
            delta = abs((now - request_date).total_seconds())
            if delta > 300:  # 5 minutes
                raise SignatureVerificationError("Request date is too far from current time (possible replay)")
        except (TypeError, ValueError) as exc:
            raise SignatureVerificationError("Invalid Date header format") from exc

    # Parse signature to get keyId
    sig_header = headers.get("Signature", "")
    sig_parts = _parse_signature_header(sig_header)
    key_id = sig_parts.get("keyId")

    if not key_id:
        raise SignatureVerificationError("Missing keyId in Signature header")

    # Extract actor URI from keyId (format: actor_uri#main-key)
    actor_uri = key_id.split("#")[0] if "#" in key_id else key_id

    # Look up cached public key
    actor = FederationActor.query.filter_by(actor_uri=actor_uri).first()

    # If actor unknown or has no public key, attempt to fetch from remote
    if not actor or not actor.public_key_pem:
        actor = _fetch_and_cache_actor_key(actor_uri, actor)

    if not actor or not actor.public_key_pem:
        raise SignatureVerificationError(f"Unknown actor: {actor_uri}")

    # Verify domain match between keyId and actor_uri (anti-spoofing)
    key_id_domain = urlparse(key_id).hostname
    actor_domain = urlparse(actor_uri).hostname
    if key_id_domain != actor_domain:
        raise SignatureVerificationError("keyId domain does not match actor URI domain")

    return verify_request(method, path, headers, body, actor.public_key_pem)


def _fetch_and_cache_actor_key(actor_uri: str, existing_actor: Any | None) -> Any | None:
    """Fetch a remote actor's profile and cache their public key.

    Args:
        actor_uri: The actor's URI.
        existing_actor: Existing FederationActor record (may have null key), or None.

    Returns:
        Updated FederationActor with public_key_pem populated, or None on failure.
    """
    from app.core.federation_client import FederationDeliveryError, SSRFError, federation_client
    from app.db import db
    from app.db.federation import FederationActor, FederationInstance, TrustLevel

    try:
        actor_data = federation_client.fetch_actor(actor_uri)
    except (SSRFError, FederationDeliveryError) as exc:
        logger.warning("Failed to fetch actor %s for key resolution: %s", actor_uri, exc)
        return None

    # Extract public key
    public_key_block = actor_data.get("publicKey", {})
    public_key_pem = public_key_block.get("publicKeyPem")
    if not public_key_pem:
        logger.warning("Actor %s has no publicKey in profile", actor_uri)
        return None

    if existing_actor:
        existing_actor.public_key_pem = public_key_pem
        existing_actor.display_name = actor_data.get("name") or existing_actor.display_name
        existing_actor.username = actor_data.get("preferredUsername") or existing_actor.username
        if actor_data.get("inbox"):
            existing_actor.inbox_url = actor_data["inbox"]
        if actor_data.get("outbox"):
            existing_actor.outbox_url = actor_data["outbox"]
        existing_actor.last_fetched_at = datetime.now(UTC)
        db.session.commit()
        return existing_actor

    # Create new actor record
    parsed = urlparse(actor_uri)
    domain = parsed.hostname
    if not domain:
        return None

    from app.core.config_service import ConfigService

    instance = FederationInstance.query.filter_by(domain=domain).first()
    if not instance:
        default_trust = ConfigService.get("FEDERATION_DEFAULT_TRUST", TrustLevel.UNTRUSTED)
        instance = FederationInstance(domain=domain, trust_level=str(default_trust))
        db.session.add(instance)
        db.session.flush()

    actor = FederationActor(
        actor_uri=actor_uri,
        inbox_url=actor_data.get("inbox", f"{actor_uri}/inbox"),
        outbox_url=actor_data.get("outbox"),
        public_key_pem=public_key_pem,
        instance_id=instance.id,
        display_name=actor_data.get("name"),
        username=actor_data.get("preferredUsername"),
        last_fetched_at=datetime.now(UTC),
    )
    db.session.add(actor)
    db.session.commit()
    return actor
