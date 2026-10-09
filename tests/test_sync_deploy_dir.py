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

"""Tests for scripts/sync_deploy_dir.py."""

from pathlib import Path

import pytest

from scripts.sync_deploy_dir import (
    main,
    sync_deploy_directory,
    verify_deploy_directory,
)


def create_source_tree(base_dir: Path) -> Path:
    src_dir = base_dir / "src_repo"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (src_dir / "docker-compose.prebuilt.yml").write_text("services: {prebuilt: true}\n", encoding="utf-8")
    (src_dir / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")

    (src_dir / "scripts").mkdir()
    (src_dir / "scripts" / "run_test.sh").write_text("#!/bin/bash\necho test\n", encoding="utf-8")
    (src_dir / "scripts" / "run_test.sh").chmod(0o755)

    (src_dir / "shared").mkdir()
    (src_dir / "shared" / "permissions.yaml").write_text("permissions: []\n", encoding="utf-8")

    (src_dir / "deploy").mkdir()
    (src_dir / "deploy" / "nginx.conf").write_text("events {}\n", encoding="utf-8")

    (src_dir / "docs" / "ontology").mkdir(parents=True)
    (src_dir / "docs" / "ontology" / "iqoqo.ttl").write_text("# owl\n", encoding="utf-8")

    return src_dir


def test_sync_initial_and_idempotent(tmp_path: Path):
    src = create_source_tree(tmp_path)
    deploy = tmp_path / "deploy_dir"

    # First sync: files created
    created, updated, removed = sync_deploy_directory(src, deploy)
    assert created > 0
    assert updated == 0
    assert removed == 0

    assert (deploy / "docker-compose.yml").is_file()
    assert not (deploy / "docker-compose.yml").is_symlink()
    assert (deploy / "scripts" / "run_test.sh").stat().st_mode & 0o111

    # Verification passes
    assert verify_deploy_directory(deploy) == 0

    # Second sync: no changes
    created, updated, removed = sync_deploy_directory(src, deploy)
    assert created == 0
    assert updated == 0
    assert removed == 0


def test_sync_replaces_symlinks_with_real_files(tmp_path: Path):
    src = create_source_tree(tmp_path)
    deploy = tmp_path / "deploy_dir"
    deploy.mkdir()

    # Pre-existing symlink in deploy dir
    (deploy / "scripts").symlink_to(src / "scripts")
    assert (deploy / "scripts").is_symlink()

    created, updated, removed = sync_deploy_directory(src, deploy)
    assert not (deploy / "scripts").is_symlink()
    assert (deploy / "scripts").is_dir()
    assert (deploy / "scripts" / "run_test.sh").is_file()
    assert not (deploy / "scripts" / "run_test.sh").is_symlink()


def test_stale_files_removed(tmp_path: Path):
    src = create_source_tree(tmp_path)
    deploy = tmp_path / "deploy_dir"

    sync_deploy_directory(src, deploy)
    assert (deploy / "scripts" / "run_test.sh").exists()

    # Delete script in source
    (src / "scripts" / "run_test.sh").unlink()

    created, updated, removed = sync_deploy_directory(src, deploy)
    assert removed == 1
    assert not (deploy / "scripts" / "run_test.sh").exists()


def test_verify_detects_drift(tmp_path: Path):
    src = create_source_tree(tmp_path)
    deploy = tmp_path / "deploy_dir"

    sync_deploy_directory(src, deploy)
    assert verify_deploy_directory(deploy) == 0

    # Modify a file in deploy dir (drift)
    (deploy / "deploy" / "nginx.conf").write_text("modified content", encoding="utf-8")
    assert verify_deploy_directory(deploy) == 1

    # Missing file
    (deploy / "docker-compose.yml").unlink()
    assert verify_deploy_directory(deploy) == 1


def test_external_symlink_in_source_rejected(tmp_path: Path):
    src = create_source_tree(tmp_path)
    deploy = tmp_path / "deploy_dir"

    external = tmp_path / "outside_dir" / "secret.txt"
    external.parent.mkdir()
    external.write_text("secret", encoding="utf-8")

    (src / "scripts" / "outside_link").symlink_to(external)

    with pytest.raises(ValueError, match="resolves outside source tree"):
        sync_deploy_directory(src, deploy)
