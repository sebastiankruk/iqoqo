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


# ---------------------------------------------------------------------------
# C18 2.4 (MOD-EXT-05) -- the two text-overlay wrappers share one implementation
#
# The drawing logic (font fallback, shrink-to-fit, wrapping, centring, stroke)
# was duplicated between the bytes and path variants at ~84% line similarity.
# It is now _draw_text_overlay(), and these tests pin the contract that makes
# the split safe: the wrappers differ only in source and destination, so they
# must produce identical pixels, and each must degrade rather than raise.
# --------------------------------------------------------------------------


def _sample_jpeg(width: int = 400, height: int = 600) -> bytes:
    """A flat-colour JPEG, enough to exercise the overlay without provider data."""
    img = PILImage.new("RGB", (width, height), (20, 40, 80))
    bio = io.BytesIO()
    img.save(bio, format="JPEG", quality=95)
    return bio.getvalue()


def test_overlay_wrappers_produce_identical_pixels(tmp_path):
    """The whole point of the extraction: same drawing, different I/O.

    If a future change reintroduces per-wrapper layout tuning, this fails.
    """
    from app.utils.images import add_text_overlay, add_text_overlay_bytes

    raw = _sample_jpeg()
    out_bytes = add_text_overlay_bytes(raw, "Dune", "Frank Herbert")

    target = tmp_path / "cover.jpg"
    target.write_bytes(raw)
    add_text_overlay(str(target), "Dune", "Frank Herbert")

    assert PILImage.open(io.BytesIO(out_bytes)).tobytes() == PILImage.open(target).tobytes()


def test_overlay_survives_long_text_that_must_shrink_and_wrap(tmp_path):
    """Exercises the iterative shrink-to-fit path, not just a short title.

    Short text fits at the initial font size, so it never enters the shrinking
    loop; only text that overflows its box reaches that code.
    """
    from app.utils.images import add_text_overlay, add_text_overlay_bytes

    raw = _sample_jpeg(200, 120)
    long_title = "A Very Long Title That Must Shrink And Wrap Across Several Lines " * 3
    long_author = " ".join(f"Author{i}" for i in range(30))

    out_bytes = add_text_overlay_bytes(raw, long_title, long_author)
    target = tmp_path / "cover.jpg"
    target.write_bytes(raw)
    add_text_overlay(str(target), long_title, long_author)

    assert out_bytes != raw, "the overlay must actually be drawn"
    assert PILImage.open(io.BytesIO(out_bytes)).tobytes() == PILImage.open(target).tobytes()


def test_overlay_bytes_returns_input_unchanged_on_undecodable_data():
    """A decode failure must degrade to an unbranded cover, not lose the image."""
    from app.utils.images import add_text_overlay_bytes

    garbage = b"this is not an image"
    assert add_text_overlay_bytes(garbage, "Title", "Author") == garbage


def test_overlay_path_variant_leaves_a_missing_file_absent(tmp_path):
    """A missing or undecodable path must be logged, not raise.

    add_text_overlay is called on the cover pipeline's success path, so an
    exception here would turn a cosmetic branding step into a failed generation.
    """
    from app.utils.images import add_text_overlay

    missing = tmp_path / "does-not-exist.jpg"
    add_text_overlay(str(missing), "Title", "Author")
    assert not missing.exists()

    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not an image either")
    add_text_overlay(str(corrupt), "Title", "Author")
    assert corrupt.read_bytes() == b"not an image either", "the file must be left untouched"
