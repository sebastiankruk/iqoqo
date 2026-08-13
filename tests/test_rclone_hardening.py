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

"""Tests for rclone subprocess command argument hardening."""

import os
from unittest.mock import MagicMock, patch

from app.core.tasks import BackupManager
from app.utils.images import optimize_and_save_image
from app.utils.llm_covers import fetch_llm_cover, generate_cover_cloud


def test_backup_manager_upload_to_glacier_delimiter() -> None:
    """Verifies upload_to_glacier uses '--' before path arguments."""
    manager = BackupManager(backup_dir="/tmp/test_backups")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.upload_to_glacier("test_backup.tar.gz")

        assert mock_run.called
        args = mock_run.call_args[0][0]
        # Check command array structure
        assert args[0:3] == ["rclone", "copy", "--s3-no-check-bucket"]
        assert args[3] == "--"
        assert args[4] == "/tmp/test_backups/test_backup.tar.gz"


def test_optimize_and_save_image_rclone_delimiter(tmp_path) -> None:
    """Verifies image cover rclone upload uses '--' delimiter."""
    test_file = str(tmp_path / "covers" / "test_cover.jpg")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)

    with patch.dict(os.environ, {"RCLONE_COVERS_REMOTE": "test_remote"}):
        with patch("subprocess.run") as mock_run:
            with patch("PIL.Image.open") as mock_img_open:
                mock_img = MagicMock()
                mock_img_open.return_value.__enter__.return_value = mock_img
                mock_img.convert.return_value = mock_img

                optimize_and_save_image(b"fake_image_bytes", test_file)

                assert mock_run.called
                args = mock_run.call_args[0][0]
                assert args[0:3] == ["rclone", "copyto", "--s3-no-check-bucket"]
                assert args[3] == "--"
                assert args[4] == test_file


def test_fetch_llm_cover_rclone_cache_delimiter() -> None:
    """Verifies LLM cover cloud cache check uses '--' delimiter."""
    with patch.dict(os.environ, {"RCLONE_COVERS_REMOTE": "test_remote"}):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            fetch_llm_cover(
                identifier="work_123",
                title="Test Book",
                author="Test Author",
                user_id="user_1",
            )

            assert mock_run.called
            args = mock_run.call_args[0][0]
            assert args[0:3] == ["rclone", "copyto", "--s3-no-check-bucket"]
            assert args[3] == "--"
