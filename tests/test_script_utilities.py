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
"""Tests for operational script utilities (extract_version, extract_changelog, validate_release)."""

import io
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.extract_changelog import extract_release_notes
from scripts.extract_version import main as extract_version_main
from scripts.validate_release import check_changelog_entry
from scripts.validate_release import main as validate_release_main


@pytest.fixture
def mock_changelog(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary CHANGELOG.md file for testing."""
    changelog_dir = tmp_path / "docs"
    changelog_dir.mkdir(parents=True, exist_ok=True)
    changelog_file = changelog_dir / "CHANGELOG.md"
    content = """# Changelog
All notable changes to this project will be documented in this file.

## [0.7.8] - 2026-07-09
### Added
- Signed backup manifest using joserfc
- BATS integration tests

## [0.7.7] - 2026-07-07
### Fixed
- Wishlist lending boundaries
"""
    changelog_file.write_text(content, encoding="utf-8")
    with patch("scripts.extract_changelog.open", mock_open_impl(changelog_file)):
        with patch("scripts.validate_release.REPO_ROOT", tmp_path):
            yield changelog_file


def mock_open_impl(file_path: Path) -> Any:
    """Helper to mock open with a specific local temp file."""
    import builtins

    original_open = builtins.open

    def _mock_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        mode = args[0] if args else kwargs.get("mode", "r")
        if "b" in mode:
            return original_open(file_path, mode=mode)
        encoding = kwargs.get("encoding", "utf-8")
        return original_open(file_path, mode=mode, encoding=encoding)

    return _mock_open


def test_extract_version_success(tmp_path: Path) -> None:
    """Test that extract_version.py successfully reads pyproject.toml."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        """[project]
name = "iqoqo"
version = "0.7.8"
""",
        encoding="utf-8",
    )

    captured_output = io.StringIO()
    with patch("scripts.extract_version.pathlib.Path", return_value=pyproject_file):
        with patch("sys.stdout", captured_output):
            extract_version_main()

    assert captured_output.getvalue().strip() == "0.7.8"


def test_extract_version_missing_file() -> None:
    """Test that extract_version.py exits when pyproject.toml is missing."""
    with patch("scripts.extract_version.pathlib.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        with pytest.raises(SystemExit) as excinfo:
            extract_version_main()
        assert "pyproject.toml not found" in str(excinfo.value)


def test_extract_changelog_success(mock_changelog: Path) -> None:
    """Test that extract_changelog.py extracts notes correctly."""
    captured_output = io.StringIO()
    with patch("sys.stdout", captured_output):
        extract_release_notes("0.7.8")

    output = captured_output.getvalue().strip()
    assert "### Added" in output
    assert "Signed backup manifest using joserfc" in output
    assert "0.7.7" not in output


def test_extract_changelog_missing_version(mock_changelog: Path) -> None:
    """Test that extract_changelog.py exits when version is not found."""
    with pytest.raises(SystemExit) as excinfo:
        extract_release_notes("0.9.9")
    assert excinfo.value.code == 1


def test_validate_release_main_success(tmp_path: Path, mock_changelog: Path) -> None:
    """Test validate_release.py main successfully passes with matching versions."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        """[project]
version = "0.7.8"
""",
        encoding="utf-8",
    )

    package_json = tmp_path / "package.json"
    package_json.write_text('{"version": "0.7.8"}', encoding="utf-8")

    frontend_package_json = tmp_path / "frontend" / "package.json"
    frontend_package_json.parent.mkdir(parents=True, exist_ok=True)
    frontend_package_json.write_text('{"version": "0.7.8"}', encoding="utf-8")

    with patch("scripts.validate_release.sys.argv", ["validate_release.py", "0.7.8"]):
        with patch("scripts.validate_release.REPO_ROOT", tmp_path):
            # Should not raise SystemExit
            validate_release_main()


def test_validate_release_main_mismatch(tmp_path: Path, mock_changelog: Path) -> None:
    """Test validate_release.py main fails when versions mismatch."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        """[project]
version = "0.7.7"
""",
        encoding="utf-8",
    )

    package_json = tmp_path / "package.json"
    package_json.write_text('{"version": "0.7.8"}', encoding="utf-8")

    with patch("scripts.validate_release.sys.argv", ["validate_release.py", "0.7.8"]):
        with patch("scripts.validate_release.REPO_ROOT", tmp_path):
            with pytest.raises(SystemExit) as excinfo:
                validate_release_main()
            assert excinfo.value.code == 1


def test_generate_admin_token_success(app: Any) -> None:
    """Test generate_admin_token.py token generation with mock user."""
    from scripts.generate_admin_token import generate_token

    mock_user = MagicMock()
    mock_user.id = "user-id-uuid"
    mock_user.email = "admin@iqoqo.local"
    mock_user.roles = []

    captured_output = io.StringIO()
    with patch("scripts.generate_admin_token.create_app", return_value=app):
        with patch("app.db.models.db.session.execute") as mock_exec:
            mock_exec.return_value.scalar_one_or_none.return_value = mock_user
            with patch("sys.stdout", captured_output):
                generate_token("admin@iqoqo.local")

    assert "TOKEN for admin@iqoqo.local:" in captured_output.getvalue()


def test_sync_permissions_verify(tmp_path: Path) -> None:
    """Test sync_permissions.py generation matching and mismatch paths."""
    yaml_file = tmp_path / "shared" / "permissions.yaml"
    yaml_file.parent.mkdir(parents=True, exist_ok=True)
    yaml_file.write_text(
        """
permissions:
  - name: "read:users"
    description: "Read users list"
""",
        encoding="utf-8",
    )

    from scripts.sync_permissions import main as sync_main

    # 1. Run sync to generate files
    mock_write = MagicMock()

    with (
        patch("sys.argv", ["sync_permissions.py"]),
        patch("pathlib.Path.write_text", mock_write),
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", mock_open_impl(yaml_file)),
    ):
        sync_main()

    # Should write to PY_OUT and TS_OUT
    assert mock_write.call_count == 2
    py_written = str(mock_write.call_args_list[0][0][0])
    ts_written = str(mock_write.call_args_list[1][0][0])
    assert "class PermissionName(StrEnum):" in py_written
    assert "export enum PermissionName {" in ts_written

    def mock_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if "permissions.ts" in str(self):
            return ts_written
        return py_written

    # 2. Run verify mode (should exit 0 since they match)
    with (
        patch("sys.argv", ["sync_permissions.py", "--verify"]),
        patch("pathlib.Path.read_text", mock_read_text),
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", mock_open_impl(yaml_file)),
    ):
        with pytest.raises(SystemExit) as excinfo:
            sync_main()
        assert excinfo.value.code == 0


def test_sync_db_permissions(app: Any) -> None:
    """Test sync_db_permissions.py runs cleanly against mock app DB."""
    from scripts.sync_db_permissions import run_sync_permissions

    mock_yaml_data = {"permissions": [{"name": "read:users", "description": "Read users"}]}

    with patch("scripts.sync_db_permissions.create_app", return_value=app):
        with patch("scripts.sync_db_permissions.open", mock_open_impl(Path("shared/permissions.yaml"))):
            with patch("scripts.sync_db_permissions.yaml.safe_load", return_value=mock_yaml_data):
                # Should not raise exceptions
                run_sync_permissions(app)


def test_rebind_covers_main(app: Any) -> None:
    """Test rebind_covers.py main execution calling utility function."""
    from scripts.rebind_covers import main as rebind_main

    with patch("scripts.rebind_covers.create_app", return_value=app):
        with patch("scripts.rebind_covers.rebind_orphaned_covers") as mock_rebind:
            mock_rebind.return_value = 5
            captured_output = io.StringIO()
            with patch("sys.stdout", captured_output):
                rebind_main()

    assert "Rebound 5 covers." in captured_output.getvalue()


def test_retry_missing_covers_dry_run(app: Any) -> None:
    """Test retry_missing_covers.py dry-run logic with mock database."""
    from scripts.retry_missing_covers import retry_missing_covers

    mock_manif = MagicMock()
    mock_manif.id = 12
    mock_manif.meta = {"title": "Failed Book", "cover_url": "http://img.jpg"}
    mock_manif.isbn13 = "978111"

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [mock_manif]

    captured_output = io.StringIO()
    with patch("scripts.retry_missing_covers.create_app", return_value=app):
        with patch("app.db.models.Manifestation.query", mock_query):
            with patch("sys.stdout", captured_output):
                retry_missing_covers(batch_limit=5, dry_run=True)

    assert "Found 1 manifestations" in captured_output.getvalue()
    assert "ID 12: Failed Book" in captured_output.getvalue()
