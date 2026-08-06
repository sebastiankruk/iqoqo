# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Tests for rclone_utils module."""

import pytest

from app.utils.rclone_utils import get_rclone_target


@pytest.mark.parametrize(
    "remote_spec,default_subpath,filename,expected",
    [
        # Simple remote name without colon
        ("iqoqo-covers", "covers", "test.jpg", "iqoqo-covers:covers/test.jpg"),
        ("iqoqo-backup", "iqoqo_backups", "", "iqoqo-backup:iqoqo_backups"),
        # Remote spec with bucket (colon)
        ("iqoqo-covers:iqoqo-covers", "covers", "test.jpg", "iqoqo-covers:iqoqo-covers/test.jpg"),
        ("iqoqo-s3:my-bucket/covers", "covers", "test.jpg", "iqoqo-s3:my-bucket/covers/test.jpg"),
        ("iqoqo-s3:my-bucket", "archives", "", "iqoqo-s3:my-bucket"),
        # Trailing slashes or whitespace
        ("  iqoqo-covers  ", "covers", "test.jpg", "iqoqo-covers:covers/test.jpg"),
        ("iqoqo-covers:  ", "covers", "test.jpg", "iqoqo-covers:covers/test.jpg"),
    ],
)
def test_get_rclone_target(remote_spec: str, default_subpath: str, filename: str, expected: str) -> None:
    """Verifies that get_rclone_target correctly builds remote target paths."""
    assert get_rclone_target(remote_spec, default_subpath, filename) == expected
