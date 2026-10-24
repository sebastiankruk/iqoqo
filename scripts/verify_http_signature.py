#!/usr/bin/env python3
"""CLI utility for verifying HTTP Signatures on ActivityPub server-to-server requests."""

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

import argparse
import base64
import hashlib
import sys
import time
from email.utils import parsedate_to_datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def parse_signature_header(header_value: str) -> dict[str, str]:
    """Parse HTTP Signature header key-value parameters."""
    params: dict[str, str] = {}
    import re

    pattern = re.compile(r'([a-zA-Z0-9_-]+)="([^"]*)"')
    for match in pattern.finditer(header_value):
        params[match.group(1)] = match.group(2)
    return params


def verify_digest(body_bytes: bytes, digest_header: str) -> bool:
    """Verify that Digest header matches SHA-256 of body."""
    if not digest_header:
        return False
    parts = digest_header.split("=", 1)
    if len(parts) != 2 or parts[0].strip().upper() != "SHA-256":
        return False

    expected_digest = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode("utf-8")
    return parts[1].strip() == expected_digest


def verify_date_skew(date_header: str, max_skew_seconds: int = 300) -> bool:
    """Verify that Date header is within acceptable time window (default 300s)."""
    try:
        req_dt = parsedate_to_datetime(date_header)
        req_timestamp = req_dt.timestamp()
        now = time.time()
        return abs(now - req_timestamp) <= max_skew_seconds
    except Exception:
        return False


def verify_rsa_signature(
    public_key_pem: bytes,
    signing_string: str,
    signature_b64: str,
) -> bool:
    """Verify RSA-SHA256 signature using cryptography."""
    try:
        public_key = load_pem_public_key(public_key_pem)
        raw_sig = base64.b64decode(signature_b64)
        public_key.verify(  # type: ignore[union-attr]
            raw_sig,
            signing_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (InvalidSignature, ValueError, TypeError) as e:
        sys.stderr.write(f"Signature verification failed: {e}\n")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify HTTP Signature for an ActivityPub request.")
    parser.add_argument("--signature", required=True, help="Value of the Signature HTTP header")
    parser.add_argument("--public-key", required=True, help="Path to public key PEM file or public key string")
    parser.add_argument("--method", default="POST", help="HTTP method (default: POST)")
    parser.add_argument("--path", default="/inbox", help="Request path (default: /inbox)")
    parser.add_argument("--host", default="localhost", help="Host header value")
    parser.add_argument("--date", help="Date header value")
    parser.add_argument("--digest", help="Digest header value")
    parser.add_argument("--body", help="Request body string or payload")

    args = parser.parse_args()

    params = parse_signature_header(args.signature)
    if not params.get("keyId") or not params.get("signature") or not params.get("headers"):
        sys.stderr.write("Error: Signature header missing keyId, signature, or headers fields.\n")
        return 1

    # Date skew verification
    if args.date and not verify_date_skew(args.date):
        sys.stderr.write("Error: Date header is outside ±300s skew window.\n")
        return 2

    # Digest verification
    if args.body and args.digest:
        if not verify_digest(args.body.encode("utf-8"), args.digest):
            sys.stderr.write("Error: Body SHA-256 does not match Digest header.\n")
            return 3

    # Reconstruct signing string
    signed_headers = params["headers"].split()
    header_map = {
        "(request-target)": f"{args.method.lower()} {args.path}",
        "host": args.host,
        "date": args.date or "",
        "digest": args.digest or "",
    }

    lines = []
    for h in signed_headers:
        val = header_map.get(h)
        if val is None:
            sys.stderr.write(f"Error: Missing value for signed header '{h}'.\n")
            return 4
        lines.append(f"{h}: {val}")

    signing_string = "\n".join(lines)

    # Read public key
    import os

    if os.path.isfile(args.public_key):
        with open(args.public_key, "rb") as f:
            pub_pem = f.read()
    else:
        pub_pem = args.public_key.encode("utf-8")

    if verify_rsa_signature(pub_pem, signing_string, params["signature"]):
        print("✅ HTTP Signature successfully verified.")
        return 0
    else:
        print("❌ HTTP Signature verification failed.")
        return 5


if __name__ == "__main__":
    sys.exit(main())
