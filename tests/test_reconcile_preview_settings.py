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


def test_reconcile_preserves_undecryptable_when_src_secret_missing_unless_purged(app):
    """Missing src_secret_key preserves undecryptable cloned rows unless purge_undecryptable=True."""
    foreign_secret = secrets.token_hex(32)
    with app.app_context():
        db.session.add(InstanceSettings(key="DISCOGS_USER_TOKEN", value=_encrypt_with_secret(foreign_secret, "discogs-val")))
        db.session.add(InstanceSettings(key="TMDB_API_KEY", value=_encrypt_with_secret(foreign_secret, "tmdb-val")))
        db.session.commit()

        preserved_summary = reconcile_preview_state(dst_env={}, src_secret_key="")
        assert preserved_summary["cleared"] == 0
        assert preserved_summary["preserved_undecryptable"] == ["DISCOGS_USER_TOKEN", "TMDB_API_KEY"]
        assert db.session.execute(db.select(InstanceSettings).filter_by(key="DISCOGS_USER_TOKEN")).scalar_one_or_none() is not None

        purged_summary = reconcile_preview_state(dst_env={}, src_secret_key="", purge_undecryptable=True)
        assert purged_summary["cleared"] == 2
        assert purged_summary["preserved_undecryptable"] == []
        assert db.session.execute(db.select(InstanceSettings).filter_by(key="DISCOGS_USER_TOKEN")).scalar_one_or_none() is None


def test_reconcile_dst_env_overrides_openobserve_and_excludes_blocklist(app):
    """Authoritative dst_env overrides OPENOBSERVE_* while CONFIG_KEY_BLOCKLIST keys are never persisted."""
    foreign_secret = secrets.token_hex(32)
    with app.app_context():
        db.session.add(InstanceSettings(key="OPENOBSERVE_BASIC_AUTH", value=_encrypt_with_secret(foreign_secret, "old-auth")))
        db.session.commit()

        summary = reconcile_preview_state(
            dst_env={
                "OPENOBSERVE_BASIC_AUTH": "bmV3OmF1dGg=",
                "OPENOBSERVE_ROOT_PASSWORD": "Strong!Password123",
                "SECRET_KEY": "should-never-be-written",
                "DATABASE_URL": "postgresql://should-not-write",
            },
            src_secret_key=foreign_secret,
        )
        assert summary["overridden"] >= 1
        assert InstanceSettings.get_value("OPENOBSERVE_BASIC_AUTH") == "bmV3OmF1dGg="
        assert InstanceSettings.get_value("SECRET_KEY") is None
        assert InstanceSettings.get_value("DATABASE_URL") is None

        # Idempotent second pass
        second = reconcile_preview_state(
            dst_env={
                "OPENOBSERVE_BASIC_AUTH": "bmV3OmF1dGg=",
                "OPENOBSERVE_ROOT_PASSWORD": "Strong!Password123",
            },
            src_secret_key=foreign_secret,
        )
        assert second["reencrypted"] == 0
        assert second["overridden"] == 0
        assert second["cleared"] == 0


def test_reconcile_main_stdin_never_leaks_secrets(app, monkeypatch, capsys):
    """CLI main() reads JSON from stdin and never echoes secret values."""
    import io

    import scripts.reconcile_preview_settings as rps

    secret_val = f"super-secret-discogs-{secrets.token_hex(6)}"
    src_key = secrets.token_hex(32)
    payload = json.dumps({"src_secret_key": src_key, "dst_env": {"DISCOGS_USER_TOKEN": secret_val}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.setattr(rps, "create_app", lambda: app)

    rc = rps.main([])
    assert rc == 0
    captured = capsys.readouterr()
    assert secret_val not in captured.out
    assert src_key not in captured.out
    assert secret_val not in captured.err


def test_main_dotenv_stdin_framed_src_secret_reencrypts_without_persisting_header(app, monkeypatch, capsys):
    """--dotenv-stdin pops __IQOQO_SRC_SECRET_KEY__= header, re-encrypts, and never stores the header."""
    import io

    from scripts.reconcile_preview_settings import main as reconcile_main

    src_key = secrets.token_hex(32)
    dst_key = app.config["SECRET_KEY"]
    secret_val = "sk-reencrypt-via-stdin-frame"

    with app.app_context():
        row = InstanceSettings(key="GEMINI_API_KEY", value=_encrypt_with_secret(src_key, secret_val))
        db.session.add(row)
        db.session.commit()

    stdin_payload = f"__IQOQO_SRC_SECRET_KEY__={src_key}\nGOOGLE_CLIENT_ID=new-gid\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_payload))
    monkeypatch.setattr("scripts.reconcile_preview_settings.create_app", lambda: app)
    monkeypatch.delenv("SRC_SECRET_KEY", raising=False)

    rc = reconcile_main(["--dotenv-stdin"])
    assert rc == 0

    captured = capsys.readouterr()
    assert "✅ Encrypted settings reconciled (re-encrypted: 1," in captured.out
    assert src_key not in captured.out
    assert secret_val not in captured.out

    with app.app_context():
        assert InstanceSettings.get_value("GEMINI_API_KEY") == secret_val
        assert InstanceSettings.get_value("__IQOQO_SRC_SECRET_KEY__") is None
        row = db.session.execute(db.select(InstanceSettings).filter_by(key="GEMINI_API_KEY")).scalar_one()
        assert isinstance(row.value, dict)
        assert row.value.get("_encrypted") is True
        assert json.loads(build_fernet_cipher(dst_key).decrypt(row.value["ciphertext"].encode()).decode()) == secret_val


def test_main_dotenv_stdin_warns_when_undecryptable_rows_preserved(app, monkeypatch, capsys):
    """Empty framed header preserves undecryptable rows and emits partial-reconcile warning."""
    import io

    from scripts.reconcile_preview_settings import main as reconcile_main

    unknown_key = secrets.token_hex(32)
    with app.app_context():
        row = InstanceSettings(key="TMDB_API_KEY", value=_encrypt_with_secret(unknown_key, "tmdb-val"))
        db.session.add(row)
        db.session.commit()

    monkeypatch.setattr("sys.stdin", io.StringIO("__IQOQO_SRC_SECRET_KEY__=\nGOOGLE_CLIENT_ID=gid\n"))
    monkeypatch.setattr("scripts.reconcile_preview_settings.create_app", lambda: app)
    monkeypatch.delenv("SRC_SECRET_KEY", raising=False)

    rc = reconcile_main(["--dotenv-stdin"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "⚠️ Encrypted settings partially reconciled" in out
    assert "preserved undecryptable: 1" in out
    assert "--purge-undecryptable" in out
