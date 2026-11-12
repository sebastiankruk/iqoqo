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
"""Tests for iqoqo_installer.py CLI and iqopresync verification checks."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.iqoqo_installer import (
    ENTROPY_REQUIRED_SECRETS,
    configure_env_content,
    generate_secure_secret,
    main,
    mask_secret,
    parse_env_file,
    run_presync_check,
)


def test_generate_secure_secret_entropy() -> None:
    """Verify secrets generate high entropy and unique values."""
    s1 = generate_secure_secret(32)
    s2 = generate_secure_secret(32)
    assert len(s1) >= 40
    assert len(s2) >= 40
    assert s1 != s2


def test_mask_secret_masks_value() -> None:
    """Verify secret masking hides middle content."""
    assert mask_secret("") == "[EMPTY]"
    assert mask_secret("short") == "***"
    assert mask_secret("supersecretkey1234567890") == "supe...7890"


def test_configure_env_content_standard_and_federation_head(tmp_path: Path) -> None:
    """Verify .env generation creates required variables and profiles."""
    example_env = tmp_path / ".env.example"
    example_env.write_text("POSTGRES_USER=iqoqo\nDATABASE_URL=postgresql://iqoqo:changeme@db:5432/iqoqo\n", encoding="utf-8")
    target_env = tmp_path / ".env"

    # Standard mode
    lines_std, vars_std = configure_env_content(
        example_env,
        target_env,
        domain="library.example.com",
        mode="standard",
        admin_email="curator@example.com",
    )
    for sec in ENTROPY_REQUIRED_SECRETS:
        assert sec in vars_std
        assert len(vars_std[sec]) >= 32
    assert vars_std["FEDERATION_HEAD_MODE"] == "false"
    assert vars_std["FEDERATION_ENABLED"] == "true"
    assert vars_std["NEXT_PUBLIC_FRONTEND_URL"] == "https://library.example.com"
    assert vars_std["ADMIN_EMAIL"] == "curator@example.com"

    # Federation Head mode
    lines_head, vars_head = configure_env_content(
        example_env,
        target_env,
        domain="hub.iqoqo.cc",
        mode="federation_head",
        admin_email="hubmaster@iqoqo.cc",
    )
    assert vars_head["FEDERATION_HEAD_MODE"] == "true"
    assert vars_head["FLASK_ENV"] == "production"


def test_installer_writes_0600_permissions_and_backup(tmp_path: Path) -> None:
    """Verify installer writes 0600 file permissions and backs up existing file."""
    env_file = tmp_path / ".env"
    example_file = tmp_path / ".env.example"
    example_file.write_text("FLASK_ENV=development\n", encoding="utf-8")

    # First write
    rc = main(
        [
            "--domain",
            "node.local",
            "--mode",
            "standard",
            "--env-file",
            str(env_file),
            "--example-file",
            str(example_file),
            "--non-interactive",
        ]
    )
    assert rc == 0
    assert env_file.exists()
    st = os.stat(env_file)
    assert stat.S_IMODE(st.st_mode) == 0o600

    # Second write triggers backup
    rc2 = main(
        [
            "--domain",
            "node.local",
            "--mode",
            "standard",
            "--env-file",
            str(env_file),
            "--example-file",
            str(example_file),
            "--non-interactive",
        ]
    )
    assert rc2 == 0
    backups = list(tmp_path.glob(".env.bak.*"))
    assert len(backups) == 1
    assert stat.S_IMODE(os.stat(backups[0]).st_mode) == 0o600


def test_production_overwrite_guard_rejects_non_interactive(tmp_path: Path) -> None:
    """Verify non-interactive mode refuses to overwrite a production .env."""
    env_file = tmp_path / ".env"
    env_file.write_text("FLASK_ENV=production\n", encoding="utf-8")
    example_file = tmp_path / ".env.example"
    example_file.write_text("FLASK_ENV=production\n", encoding="utf-8")

    rc = main(
        [
            "--domain",
            "prod.iqoqo.cc",
            "--env-file",
            str(env_file),
            "--example-file",
            str(example_file),
            "--non-interactive",
        ]
    )
    assert rc == 1


def test_run_presync_check_success_and_failure(tmp_path: Path) -> None:
    """Verify iqopresync diagnostic reporting."""
    env_file = tmp_path / ".env"

    # Fails when missing
    assert run_presync_check(env_file) == 2

    # Fails when secrets weak
    env_file.write_text(
        "SECRET_KEY=changeme\nJWT_SECRET_KEY=short\nPOSTGRES_PASSWORD=pass\nREDIS_PASSWORD=pass\n",
        encoding="utf-8",
    )
    os.chmod(env_file, 0o600)
    assert run_presync_check(env_file) == 2

    # Passes when secrets secure
    s = generate_secure_secret(32)
    env_file.write_text(
        f"SECRET_KEY={s}\nJWT_SECRET_KEY={s}\nPOSTGRES_PASSWORD={s}\nREDIS_PASSWORD={s}\nADMIN_PASSWORD={s}\nNEXT_PUBLIC_FRONTEND_URL=http://localhost:5000\n",
        encoding="utf-8",
    )
    assert run_presync_check(env_file) == 0


def test_configure_env_content_percent_encodes_postgres_password(tmp_path: Path) -> None:
    """Verify preserved POSTGRES_PASSWORD with URI-reserved chars is percent-encoded in DATABASE_URL."""
    example_env = tmp_path / ".env.example"
    example_env.write_text("POSTGRES_USER=iqoqo\nDATABASE_URL=postgresql://iqoqo:changeme@db:5432/iqoqo\n", encoding="utf-8")
    target_env = tmp_path / ".env"

    _, vars_out = configure_env_content(
        example_env,
        target_env,
        domain="library.example.com",
        mode="standard",
        admin_email="curator@example.com",
        rotate_secrets=False,
        existing_vars={"POSTGRES_PASSWORD": "p@ss:w/o?rd#1234567890123456"},
    )
    assert vars_out["DATABASE_URL"] == "postgresql://iqoqo:p%40ss%3Aw%2Fo%3Frd%231234567890123456@db:5432/iqoqo"


def test_run_presync_check_probes_status_and_webfinger(tmp_path: Path, monkeypatch) -> None:
    """Verify iqopresync probes /api/health, /api/system/status, nodeinfo, and webfinger."""
    env_file = tmp_path / ".env"
    s = generate_secure_secret(32)
    env_file.write_text(
        f"SECRET_KEY={s}\nJWT_SECRET_KEY={s}\nPOSTGRES_PASSWORD={s}\nREDIS_PASSWORD={s}\nADMIN_PASSWORD={s}\nNEXT_PUBLIC_FRONTEND_URL=https://node.example.com\n",
        encoding="utf-8",
    )
    os.chmod(env_file, 0o600)

    probed_urls: list[str] = []

    class _FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(req, timeout=3):  # noqa: ARG001
        probed_urls.append(req.full_url)
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    assert run_presync_check(env_file) == 0
    assert "https://node.example.com/api/health" in probed_urls
    assert "https://node.example.com/api/system/status" in probed_urls
    assert "https://node.example.com/.well-known/nodeinfo" in probed_urls
    assert "https://node.example.com/.well-known/webfinger" in probed_urls
