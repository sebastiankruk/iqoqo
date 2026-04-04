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

import cv2
import numpy as np
from PIL import Image

from app.utils.images import optimize_and_save_image, smart_crop_and_warp


def create_test_image_with_rectangle():
    """Creates a black background image with a skewed white rectangle representing a book."""
    img = np.zeros((500, 500, 3), dtype=np.uint8)

    # Draw a skewed white polygon (mimicking a photo of a book on a table)
    pts = np.array([[100, 150], [400, 100], [450, 400], [50, 450]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(img, [pts], (255, 255, 255))

    # Encode to jpg bytes
    _, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()


def test_smart_crop_and_warp_success():
    """Tests that a clear rectangle is detected and warped properly."""
    raw_bytes = create_test_image_with_rectangle()
    cropped_bytes, mime_type = smart_crop_and_warp(raw_bytes, "image/png")

    assert mime_type == "image/jpeg"

    # Decode and check dimensions
    nparr = np.frombuffer(cropped_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # The warped image should be roughly rectangular bounds of that object.
    assert img.shape[0] > 200
    assert img.shape[1] > 200
    assert cropped_bytes != raw_bytes


def test_smart_crop_fallback_on_solid_color():
    """Tests that if no clear rectangle exists (solid color), original image and mime are returned."""
    # Create pure black image (no edges)
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    _, buffer = cv2.imencode(".jpg", img)
    raw_bytes = buffer.tobytes()

    cropped_bytes, mime_type = smart_crop_and_warp(raw_bytes, "image/jpeg")
    assert cropped_bytes == raw_bytes
    assert mime_type == "image/jpeg"


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
    optimize_and_save_image(buffer.getvalue(), str(filepath), apply_smart_crop=False)

    # Check it saved
    assert filepath.exists()

    # Verify thumbnail constraints and JPEG normalization
    with Image.open(filepath) as out_img:
        assert out_img.format == "JPEG"
        assert max(out_img.size) <= 1024
