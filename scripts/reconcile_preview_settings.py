#!/usr/bin/env python3
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
"""Reconcile cloned InstanceSettings and authoritative preview credentials.

Reads a JSON payload from stdin (so source SECRET_KEY and destination .env
credentials never touch disk or process argv):
  {
    "src_secret_key": "<optional source SECRET_KEY>",
    "dst_env": {"KEY": "VALUE", ...}
  }

1. Decrypts cloned encrypted InstanceSettings rows using src_secret_key when
   preview's SECRET_KEY raises InvalidToken, and re-encrypts them in-place.
2. Applies authoritative overrides from dst_env (Google OAuth, OpenObserve,
   and any explicitly configured lookup keys) into InstanceSettings.
3. Syncs ADMIN_EMAIL / ADMIN_PASSWORD from dst_env into the User table.
4. Reports Google OAuth and external lookup API readiness without printing
   any secret values, keeping AI credentials optional.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # pylint: disable=wrong-import-position
from app.api.admin import API_KEYS  # pylint: disable=wrong-import-position
from app.core.config_service import CONFIG_KEY_BLOCKLIST  # pylint: disable=wrong-import-position
from app.db import db  # pylint: disable=wrong-import-position
from app.db.auth import Role, User  # pylint: disable=wrong-import-position
from app.db.settings import (  # pylint: disable=wrong-import-position
    SENSITIVE_SETTING_KEYS,
    InstanceSettings,
    _get_fernet_cipher,
    encrypt_setting_value,
)

ELIGIBLE_SETTING_KEYS: frozenset[str] = frozenset((set(API_KEYS) | set(SENSITIVE_SETTING_KEYS)) - set(CONFIG_KEY_BLOCKLIST))

LOOKUP_PROVIDERS: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("Google Books", (("GOOGLE_BOOKS_API_KEY",),)),
    ("Discogs", (("DISCOGS_USER_TOKEN",), ("DISCOGS_CONSUMER_KEY", "DISCOGS_CONSUMER_SECRET"))),
    ("TMDB", (("TMDB_API_READ_ACCESS_TOKEN",), ("TMDB_API_KEY",))),
    ("BoardGameGeek", (("BGG_API_TOKEN",),)),
    ("Allegro", (("ALLEGRO_CLIENT_ID", "ALLEGRO_CLIENT_SECRET"),)),
    ("IGDB / Twitch", (("IGDB_CLIENT_ID", "IGDB_CLIENT_SECRET"), ("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET"))),
    ("UPC Databases", (("UPC_ITEM_DB_KEY",), ("UPC_DATABASE_ORG_KEY",))),
    ("Rebrickable", (("REBRICKABLE_API_KEY",),)),
)


def build_fernet_cipher(secret: str) -> Fernet:
    """Derive a Fernet cipher from an explicit SECRET_KEY string."""
    key_bytes = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key_bytes)


def _strip_quotes(val: str) -> str:
    """Strip surrounding single or double quotes and whitespace."""
    cleaned = val.strip()
    if len(cleaned) >= 2 and ((cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'"))):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _provider_configured(configured_keys: set[str], alternatives: tuple[tuple[str, ...], ...]) -> bool:
    """Return True if any credential group in alternatives is fully configured."""
    return any(all(key in configured_keys for key in group) for group in alternatives)


def reconcile_preview_state(
    dst_env: dict[str, str],
    src_secret_key: str = "",
) -> dict[str, Any]:
    """Re-encrypt cloned settings, push dst_env overrides, sync admin, and audit APIs.

    Must be called within an active Flask application context.
    """
    dst_cipher = _get_fernet_cipher()
    src_cipher = build_fernet_cipher(src_secret_key) if src_secret_key.strip() else None

    clean_env: dict[str, str] = {}
    for k, v in dst_env.items():
        if isinstance(k, str) and isinstance(v, str):
            cleaned = _strip_quotes(v)
            if cleaned:
                clean_env[k.strip()] = cleaned

    reencrypted = 0
    cleared = 0
    overridden = 0

    rows = db.session.execute(db.select(InstanceSettings)).scalars().all()
    for row in rows:
        if row.key in ELIGIBLE_SETTING_KEYS and row.key in clean_env:
            # Destination .env explicitly overrides this key below.
            continue

        stored = row.value
        if not (isinstance(stored, dict) and stored.get("_encrypted") is True and isinstance(stored.get("ciphertext"), str)):
            continue

        ciphertext_bytes = stored["ciphertext"].encode("utf-8")
        try:
            dst_cipher.decrypt(ciphertext_bytes)
            continue
        except InvalidToken:
            pass

        if src_cipher is not None:
            try:
                decrypted_raw = src_cipher.decrypt(ciphertext_bytes)
                decrypted_val = json.loads(decrypted_raw.decode("utf-8"))
                row.value = encrypt_setting_value(row.key, decrypted_val)
                reencrypted += 1
                continue
            except (InvalidToken, ValueError, json.JSONDecodeError):
                pass

        db.session.delete(row)
        cleared += 1

    # Push authoritative destination .env settings into DB
    for key in sorted(ELIGIBLE_SETTING_KEYS):
        val = clean_env.get(key)
        if not val:
            continue
        existing = InstanceSettings.get_value(key)
        if existing != val:
            InstanceSettings.set_value(key, val, commit=False)
            overridden += 1

    # Sync local preview ADMIN_EMAIL / ADMIN_PASSWORD into User table
    admin_email = clean_env.get("ADMIN_EMAIL") or _strip_quotes(os.environ.get("ADMIN_EMAIL", ""))
    admin_password = clean_env.get("ADMIN_PASSWORD") or _strip_quotes(os.environ.get("ADMIN_PASSWORD", ""))
    admin_synced = False
    admin_warning: str | None = None

    if admin_email and admin_password:
        if len(admin_password) < 8:
            admin_warning = "ADMIN_PASSWORD is shorter than 8 characters; skipping admin user password sync."
        else:
            admin_role = db.session.execute(db.select(Role).filter_by(name="admin")).scalar_one_or_none()
            admin_user = db.session.execute(db.select(User).filter_by(email=admin_email)).scalar_one_or_none()
            if admin_user is None:
                admin_user = User(email=admin_email, display_name="Administrator", is_active=True)
                db.session.add(admin_user)
            else:
                admin_user.is_active = True
            admin_user.set_password(admin_password)
            if admin_role is not None and admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
            admin_synced = True

    if reencrypted or cleared or overridden or admin_synced:
        db.session.commit()

    configured_keys = set(InstanceSettings.get_configured_keys()) | set(clean_env.keys())
    google_oauth_ok = "GOOGLE_CLIENT_ID" in configured_keys and "GOOGLE_CLIENT_SECRET" in configured_keys

    lookup_present: list[str] = []
    lookup_missing: list[str] = []
    for name, alternatives in LOOKUP_PROVIDERS:
        if _provider_configured(configured_keys, alternatives):
            lookup_present.append(name)
        else:
            lookup_missing.append(name)

    return {
        "reencrypted": reencrypted,
        "cleared": cleared,
        "overridden": overridden,
        "admin_synced": admin_synced,
        "admin_email": admin_email if admin_synced else None,
        "admin_warning": admin_warning,
        "google_oauth_ok": google_oauth_ok,
        "lookup_present": lookup_present,
        "lookup_missing": lookup_missing,
    }


def main() -> int:
    """CLI entrypoint reading JSON reconciliation payload from stdin."""
    raw_stdin = sys.stdin.read().strip()
    payload: dict[str, Any] = json.loads(raw_stdin) if raw_stdin else {}
    src_secret_key = str(payload.get("src_secret_key") or "")
    raw_env = payload.get("dst_env")
    dst_env: dict[str, str] = raw_env if isinstance(raw_env, dict) else {}

    # Suppress expected pre-reconciliation InvalidToken startup logs while building the app
    app_logger = logging.getLogger("app")
    prev_level = app_logger.level
    app_logger.setLevel(logging.CRITICAL)
    try:
        app = create_app()
    finally:
        app_logger.setLevel(prev_level)
    with app.app_context():
        summary = reconcile_preview_state(dst_env=dst_env, src_secret_key=src_secret_key)

    print(
        f"✅ Encrypted settings reconciled (re-encrypted: {summary['reencrypted']}, "
        f"overridden from env: {summary['overridden']}, cleared stale: {summary['cleared']})"
    )
    if summary["admin_synced"]:
        print(f"👤 Synced preview admin credentials for {summary['admin_email']}")
    elif summary["admin_warning"]:
        print(f"⚠️ {summary['admin_warning']}")

    if summary["google_oauth_ok"]:
        print("🔐 Google OAuth credentials configured (DB/env)")
    else:
        print("⚠️ WARNING: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing from both DB and destination .env — Google login disabled")

    if summary["lookup_present"]:
        print(f"🔎 Lookup APIs ready: {', '.join(summary['lookup_present'])}")
    if summary["lookup_missing"]:
        print(f"⚠️ Missing lookup APIs: {', '.join(summary['lookup_missing'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
