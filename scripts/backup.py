"""Script to create a backup of the iQoQo database and cover images."""

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

import base64
import json
import logging
import os
import shutil
import sys
from datetime import datetime

from joserfc import jwt as jose_jwt
from joserfc.jwk import OctKey

from app import create_app
from app.config import Config
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


def _b64url_encode(value: str) -> str:
    """Encode a raw string as base64url with correct padding for OctKey import.

    joserfc OctKey.import_key expects the ``k`` parameter of a JWK to be
    base64url-encoded (RFC 7517 §6.4).  When callers pass a plain ASCII
    secret we encode it here so the rest of the codebase stays clean.
    """
    raw = value.encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_backup_manifest_token(payload: dict, secret_key: str) -> str:
    """Generate a signed JWT manifest token for backup authenticity using joserfc.

    This token proves the backup was created by a trusted iqoqo instance and
    allows downstream restore scripts to verify archive integrity before applying.

    Args:
        payload: Dictionary of claims to embed in the JWT (e.g. timestamp, version).
        secret_key: HMAC secret key string used for HS256 signing.

    Returns:
        A compact-serialised JWT string (header.payload.signature).

    Raises:
        Exception: Re-raises any joserfc or cryptography errors.
    """
    try:
        key = OctKey.import_key({"use": "sig", "kty": "oct", "k": _b64url_encode(secret_key)})
        header = {"alg": "HS256"}
        token = jose_jwt.encode(header, payload, key)
        return token
    except Exception:
        logger.error("Failed to generate backup manifest token", exc_info=True)
        raise


def create_export(app=None):
    """Creates a full backup archive of data and covers.

    Generates a time-stamped zip containing:
    - metadata.json: full DB export via DataManager
    - manifest.jwt:  joserfc-signed token proving authenticity and version

    The manifest token allows restore scripts to verify the archive was
    produced by a trusted iqoqo instance before applying destructive changes.
    """
    if app is None:
        app = create_app()
    with app.app_context():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Prioritize app config over env var for backup destination
        export_base_dir = app.config.get("BACKUP_DIR") or os.environ.get("BACKUP_DIR", os.path.join(Config.BASE_DIR, "exports"))
        backup_dir_name = f"iqoqo_backup_{timestamp}"
        export_dir = os.path.join(export_base_dir, backup_dir_name)

        os.makedirs(export_dir, exist_ok=True)
        print(f"Starting backup to {export_dir}...")

        # 1. Export JSON Metadata
        print("Exporting database...")
        data = DataManager.export_all()
        with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 2. Generate signed manifest JWT (joserfc HS256) for archive authenticity
        secret_key = app.config.get("SECRET_KEY") or os.environ.get("IQOQO_SECRET_KEY", "default-iqoqo-dev-secret")
        manifest_payload = {
            "iss": "iqoqo-backup",
            "timestamp": timestamp,
            "version": app.config.get("VERSION", "unknown"),
            "type": "full_archive",
        }
        manifest_token = generate_backup_manifest_token(manifest_payload, secret_key)
        manifest_jwt_path = os.path.join(export_dir, "manifest.jwt")
        with open(manifest_jwt_path, "w", encoding="utf-8") as f:
            f.write(manifest_token)
        print("Signed backup manifest generated.")

        # 3. Copy the covers directory
        print("Archiving covers...")
        covers_source = os.path.join(Config.BASE_DIR, "app", "static", "covers")
        covers_dest = os.path.join(export_dir, "covers")
        if os.path.exists(covers_source):
            shutil.copytree(covers_source, covers_dest)

        # 4. Zip the archive
        print("Compressing archive...")
        archive_path = shutil.make_archive(os.path.join(export_base_dir, backup_dir_name), "zip", export_dir)

        # Cleanup unzipped folder
        shutil.rmtree(export_dir)
        print(f"✅ Export complete: {archive_path}")


if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    create_export()
