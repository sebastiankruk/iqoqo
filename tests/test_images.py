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
from unittest import mock

from PIL import Image

from app.utils.images import is_valid_cover, optimize_and_save_image


def test_optimize_and_save_image_handles_exif_transpose(tmp_path):
    """
    Ensures that ImageOps.exif_transpose is called during image optimization
    to fix 90-degree smartphone rotation bugs.
    """
    # Create a dummy image
    dummy_img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    dummy_img.save(img_byte_arr, format="JPEG")
    img_bytes = img_byte_arr.getvalue()

    out_file = tmp_path / "test_optimized.jpg"

    # Patch ImageOps.exif_transpose to verify it is called
    with mock.patch("app.utils.images.ImageOps.exif_transpose", return_value=dummy_img) as mock_transpose:
        optimize_and_save_image(img_bytes, str(out_file))

        mock_transpose.assert_called_once()
        assert out_file.exists()


def test_is_valid_cover_rejects_empty():
    assert is_valid_cover(b"") is False


def test_is_valid_cover_rejects_small_payloads():
    # Less than 1000 bytes should be rejected
    assert is_valid_cover(b"a" * 500) is False
