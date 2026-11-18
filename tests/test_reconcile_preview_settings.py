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

"""Tests for scripts/reconcile_preview_settings.py (C122)."""

from __future__ import annotations

import json
import secrets

from app.db import db
from app.db.auth import Role, User
from app.db.settings import InstanceSettings
from scripts.reconcile_preview_settings import build_fernet_cipher, reconcile_preview_state


def _encrypt_with_secret(secret_key: str, value: str) -> dict[str, object]:
    """Simulate a cloned PROD InstanceSettings row encrypted under a foreign SECRET_KEY."""
    cipher = build_fernet_cipher(secret_key)
    ciphertext = cipher.encrypt(json.dumps(value).encode("utf-8")).decode("utf-8")
    return {"_encrypted": True, "ciphertext": ciphertext}


def test_reconcile_reencrypts_cloned_prod_secrets_and_pushes_dst_overrides(app):
    """Cloned PROD lookup keys are re-encrypted under preview SECRET_KEY while $DST_LOC/.env wins for OAuth/admin."""
    prod_secret = secrets.token_hex(32)
    prod_discogs = f"prod-discogs-{secrets.token_hex(6)}"
    prod_tmdb = f"prod-tmdb-{secrets.token_hex(6)}"
    prod_google_id = f"prod-google-id-{secrets.token_hex(4)}"
    preview_google_id = f"preview-google-id-{secrets.token_hex(4)}"
    preview_google_secret = f"preview-google-secret-{secrets.token_hex(4)}"
    preview_admin_pw = f"PreviewAdmin!{secrets.token_hex(4)}"

    with app.app_context():
        # Seed cloned PROD encrypted rows (encrypted with prod_secret, NOT app SECRET_KEY)
        db.session.add(InstanceSettings(key="DISCOGS_USER_TOKEN", value=_encrypt_with_secret(prod_secret, prod_discogs)))
        db.session.add(InstanceSettings(key="TMDB_API_KEY", value=_encrypt_with_secret(prod_secret, prod_tmdb)))
        db.session.add(InstanceSettings(key="GOOGLE_CLIENT_ID", value=_encrypt_with_secret(prod_secret, prod_google_id)))
        db.session.add(InstanceSettings(key="BGG_API_TOKEN", value=_encrypt_with_secret("unknown-other-key", "stale-val")))
        if db.session.execute(db.select(Role).filter_by(name="admin")).scalar_one_or_none() is None:
            db.session.add(Role(name="admin"))
        db.session.commit()

        summary = reconcile_preview_state(
            dst_env={
                "ADMIN_EMAIL": "preview-admin@iqoqo.local",
                "ADMIN_PASSWORD": preview_admin_pw,
                "GOOGLE_CLIENT_ID": preview_google_id,
                "GOOGLE_CLIENT_SECRET": preview_google_secret,
            },
            src_secret_key=prod_secret,
        )

        # Cloned Discogs & TMDB survived re-encryption; unrecoverable BGG row was cleared
        assert summary["reencrypted"] == 2
        assert summary["cleared"] == 1
        assert summary["overridden"] == 2
        assert summary["admin_synced"] is True
        assert summary["google_oauth_ok"] is True

        assert InstanceSettings.get_value("DISCOGS_USER_TOKEN") == prod_discogs
        assert InstanceSettings.get_value("TMDB_API_KEY") == prod_tmdb
        # Authoritative $DST_LOC/.env Google OAuth overwrote cloned PROD OAuth
        assert InstanceSettings.get_value("GOOGLE_CLIENT_ID") == preview_google_id
        assert InstanceSettings.get_value("GOOGLE_CLIENT_SECRET") == preview_google_secret
        assert InstanceSettings.get_value("BGG_API_TOKEN") is None

        # Admin user created/synced with admin role and preview password
        admin_user = db.session.execute(db.select(User).filter_by(email="preview-admin@iqoqo.local")).scalar_one()
        assert admin_user.check_password(preview_admin_pw) is True
        assert any(r.name == "admin" for r in admin_user.roles)

        # AI keys are optional and never flagged in lookup_missing
        assert "Discogs" in summary["lookup_present"]
        assert "TMDB" in summary["lookup_present"]
        assert "BoardGameGeek" in summary["lookup_missing"]
        assert not any("OpenAI" in item or "Gemini" in item for item in summary["lookup_missing"])
