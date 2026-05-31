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
"""RSA key management for ActivityPub federation actors."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)

# Keys stored under data/keys/ relative to project root
_KEYS_DIR = Path(os.environ.get("FEDERATION_KEYS_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data", "keys")))


def _ensure_keys_dir() -> Path:
    """Create the keys directory if it doesn't exist."""
    keys_dir = _KEYS_DIR.resolve()
    keys_dir.mkdir(parents=True, exist_ok=True)
    return keys_dir


def generate_actor_keypair(user_id: str) -> tuple[str, str]:
    """Generate an RSA-2048 keypair for a federation actor.

    Args:
        user_id: UUID string of the local user.

    Returns:
        Tuple of (key_id_suffix, public_key_pem) where key_id_suffix is
        used to construct the full key ID URI.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Serialize private key to PEM (no encryption — file-system security only)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key to PEM
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Store private key on filesystem with restrictive permissions
    keys_dir = _ensure_keys_dir()
    key_path = keys_dir / f"{user_id}.pem"
    key_path.write_bytes(private_pem)
    os.chmod(key_path, 0o600)

    key_id_suffix = "#main-key"
    public_key_str = public_pem.decode("utf-8")

    logger.info("Generated federation keypair for user %s", user_id)
    return key_id_suffix, public_key_str


def get_actor_private_key(user_id: str) -> rsa.RSAPrivateKey | None:
    """Load the private key for a federation actor from filesystem.

    Args:
        user_id: UUID string of the local user.

    Returns:
        RSAPrivateKey instance or None if key doesn't exist.
    """
    keys_dir = _KEYS_DIR.resolve()
    key_path = keys_dir / f"{user_id}.pem"

    if not key_path.exists():
        return None

    private_pem = key_path.read_bytes()
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    return private_key  # type: ignore[return-value]


def get_actor_public_key(user_id: str) -> str | None:
    """Get the public key PEM for a federation actor.

    Reads from the User model's federation_public_key column.
    Falls back to deriving from the private key file if column is empty.

    Args:
        user_id: UUID string of the local user.

    Returns:
        Public key PEM string or None if no key exists.
    """
    # Try deriving from private key
    private_key = get_actor_private_key(user_id)
    if private_key is None:
        return None

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_pem.decode("utf-8")


def delete_actor_keypair(user_id: str) -> bool:
    """Delete the keypair for a federation actor.

    Args:
        user_id: UUID string of the local user.

    Returns:
        True if key was deleted, False if it didn't exist.
    """
    keys_dir = _KEYS_DIR.resolve()
    key_path = keys_dir / f"{user_id}.pem"

    if key_path.exists():
        key_path.unlink()
        logger.info("Deleted federation keypair for user %s", user_id)
        return True
    return False
