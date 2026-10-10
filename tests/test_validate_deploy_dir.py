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

"""Tests for scripts/validate_deploy_dir.py."""

from pathlib import Path

import pytest

from scripts.validate_deploy_dir import (
    Violation,
    format_report,
    main,
    validate_deployment_dir,
)


def create_clean_deploy_dir(base_dir: Path) -> Path:
    deploy_dir = base_dir / "clean_deploy"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / ".env").write_text("MODE=preview\n", encoding="utf-8")
    (deploy_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / "scripts").mkdir()
    (deploy_dir / "shared").mkdir()
    (deploy_dir / "deploy").mkdir()
    (deploy_dir / "deploy" / "nginx.conf").write_text("events {}\n", encoding="utf-8")
    (deploy_dir / "docs" / "ontology").mkdir(parents=True)
    (deploy_dir / "docs" / "ontology" / "iqoqo.ttl").write_text("# ttl\n", encoding="utf-8")
    (deploy_dir / ".allegro_token.json").write_text("{}\n", encoding="utf-8")
    return deploy_dir


def test_clean_deployment_dir(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    violations = validate_deployment_dir(deploy_dir)
    assert len(violations) == 0
    assert main([str(deploy_dir)]) == 0


def test_missing_env_file(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    (deploy_dir / ".env").unlink()

    violations = validate_deployment_dir(deploy_dir)
    kinds = [v.kind for v in violations]
    assert "Required Environment Configuration" in kinds
    assert main([str(deploy_dir)]) == 1


def test_missing_compose_file(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    (deploy_dir / "docker-compose.yml").unlink()

    violations = validate_deployment_dir(deploy_dir)
    kinds = [v.kind for v in violations]
    assert "Required Compose Specification" in kinds


def test_file_mount_is_directory(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    (deploy_dir / ".allegro_token.json").unlink()
    (deploy_dir / ".allegro_token.json").mkdir()

    violations = validate_deployment_dir(deploy_dir)
    kinds = [v.kind for v in violations]
    assert "Invalid File-Target Mount Type" in kinds
    assert any(".allegro_token.json" in v.path for v in violations)


def test_external_symlink_rejected(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    external_scripts = tmp_path / "external_repo" / "scripts"
    external_scripts.mkdir(parents=True)

    import shutil

    shutil.rmtree(deploy_dir / "scripts")
    (deploy_dir / "scripts").symlink_to(external_scripts)

    violations = validate_deployment_dir(deploy_dir)
    kinds = [v.kind for v in violations]
    assert "External Symlink Escaping Deployment Directory" in kinds


def test_intra_directory_symlink_permitted(tmp_path: Path):
    deploy_dir = create_clean_deploy_dir(tmp_path)
    internal_scripts = deploy_dir / "real_scripts"
    internal_scripts.mkdir()

    import shutil

    shutil.rmtree(deploy_dir / "scripts")
    (deploy_dir / "scripts").symlink_to(internal_scripts)

    violations = validate_deployment_dir(deploy_dir)
    # Should not report external symlink
    assert not any("External Symlink" in v.kind for v in violations)


def test_multiple_violations_reported_in_one_pass(tmp_path: Path):
    empty_dir = tmp_path / "empty_deploy"
    empty_dir.mkdir()
    (empty_dir / ".allegro_token.json").mkdir()

    violations = validate_deployment_dir(empty_dir)
    kinds = [v.kind for v in violations]
    assert "Required Environment Configuration" in kinds
    assert "Required Compose Specification" in kinds
    assert "Invalid File-Target Mount Type" in kinds

    report = format_report(violations)
    assert "Required Environment Configuration (1)" in report
    assert "Required Compose Specification (1)" in report
    assert "Total violations: 3" in report
