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

import io
from unittest.mock import MagicMock

import pytest
from PIL import Image as PILImage

from app.utils.images import validate_upload_file


def test_validate_upload_file_valid_jpg():
    """Test valid JPEG upload passes validation."""
    img = PILImage.new("RGB", (10, 10), color="white")
    bio = io.BytesIO()
    img.save(bio, format="JPEG")
    bio.filename = "test.jpg"
    bio.seek(0)

    assert validate_upload_file(bio) == "jpg"


def test_validate_upload_file_invalid_extension():
    """Test invalid extension fails validation."""
    mock_file = MagicMock()
    mock_file.filename = "malicious.exe"

    with pytest.raises(ValueError, match="Invalid file type"):
        validate_upload_file(mock_file)


def test_validate_upload_file_too_large():
    """Test oversized file fails validation."""
    mock_file = MagicMock()
    mock_file.filename = "huge.png"
    mock_file.seek.side_effect = lambda *args, **kwargs: None
    mock_file.tell.return_value = 20 * 1024 * 1024  # 20MB

    with pytest.raises(ValueError, match="File too large"):
        validate_upload_file(mock_file, max_size_bytes=10 * 1024 * 1024)


def test_validate_upload_file_corrupt_image():
    """Test corrupt image data fails validation."""
    bio = io.BytesIO(b"not an image at all")
    bio.filename = "fake.webp"

    with pytest.raises(ValueError, match="Invalid or corrupted image file"):
        validate_upload_file(bio)


def test_validate_upload_file_no_file():
    """Test missing file fails validation."""
    with pytest.raises(ValueError, match="No file provided"):
        validate_upload_file(None)

    mock_file = MagicMock()
    mock_file.filename = ""
    with pytest.raises(ValueError, match="No file provided"):
        validate_upload_file(mock_file)
