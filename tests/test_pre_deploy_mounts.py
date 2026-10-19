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
"""Tests for scripts/pre_deploy_mounts.py permission and mount guards."""

from __future__ import annotations

import os
from pathlib import Path

from scripts.pre_deploy_mounts import DIRECTORY_MOUNTS, prepare_deploy_mounts


def test_prepare_deploy_mounts_enforces_key_permissions(tmp_path: Path) -> None:
    """Verify data/keys is set to 0700 and *.pem files are set to 0600."""
    keys_dir = tmp_path / "data" / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(keys_dir, 0o777)

    pem_file = keys_dir / "actor_private_key.pem"
    pem_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n", encoding="utf-8")
    os.chmod(pem_file, 0o666)

    # Secrets files
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET_KEY=test-secret\n", encoding="utf-8")
    os.chmod(env_file, 0o644)

    ret = prepare_deploy_mounts(tmp_path)
    assert ret == 0

    # Assert directory permissions
    assert keys_dir.stat().st_mode & 0o777 == 0o700
    assert pem_file.stat().st_mode & 0o777 == 0o600
    assert env_file.stat().st_mode & 0o777 == 0o600

    # Assert standard directory mounts exist
    for rel_dir in DIRECTORY_MOUNTS:
        target = tmp_path / rel_dir
        assert target.exists()
        assert target.is_dir()


def test_prepare_deploy_mounts_repairs_allegro_token_directory(tmp_path: Path) -> None:
    """Verify empty .allegro_token.json directory is replaced with 0600 regular file."""
    token_dir = tmp_path / ".allegro_token.json"
    token_dir.mkdir(parents=True, exist_ok=True)

    ret = prepare_deploy_mounts(tmp_path)
    assert ret == 0

    assert token_dir.is_file()
    assert token_dir.stat().st_mode & 0o777 == 0o600
    assert token_dir.read_text(encoding="utf-8") == "{}\n"


def test_prepare_deploy_mounts_rejects_non_empty_allegro_directory(tmp_path: Path) -> None:
    """Verify non-empty .allegro_token.json directory triggers an error code."""
    token_dir = tmp_path / ".allegro_token.json"
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / "stray.txt").write_text("corrupted", encoding="utf-8")

    ret = prepare_deploy_mounts(tmp_path)
    assert ret != 0
