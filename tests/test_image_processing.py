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
# pylint: disable=no-member
import io

from PIL import Image

from app.utils.images import optimize_and_save_image


def test_optimize_and_save_image_normalization(tmp_path):
    """
    Tests that optimize_and_save_image correctly saves, resizes, and normalizes
    images to JPEG format.
    """
    filepath = tmp_path / "test_norm.jpg"

    # Create a small PNG image
    img = Image.new("RGB", (2000, 1000), color="blue")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    # We test that the function executes without error, resizes, and saves as JPEG.
    optimize_and_save_image(buffer.getvalue(), str(filepath))

    # Check it saved
    assert filepath.exists()

    # Verify thumbnail constraints and JPEG normalization
    with Image.open(filepath) as out_img:
        assert out_img.format == "JPEG"
        assert max(out_img.size) <= 1024
