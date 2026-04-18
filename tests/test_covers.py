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
import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import requests
from PIL import Image

from app.db.models import Manifestation
from app.utils.covers import (
    MAX_COVER_FILE_SIZE,
    MIN_COVER_FILE_SIZE,
    download_direct_url,
    fetch_external_api_cover,
    generate_fallback_cover,
    process_cover_pipeline,
)
from app.utils.images import is_valid_cover, optimize_and_save_image
from app.utils.llm_covers import generate_cover_cloud


@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock:
        yield mock


def test_generate_fallback_cover(tmp_path):
    """Test that Pillow generates a file."""
    # Override COVERS_DIR for test
    with patch("app.utils.covers.COVERS_DIR", str(tmp_path)):
        path = generate_fallback_cover("12345", "Test Book", "Test Author")
        assert path is not None
        assert "12345_generated.jpg" in path
        assert (tmp_path / "12345_generated.jpg").exists()


def test_fetch_external_api_cover_openlibrary(mock_requests_get, tmp_path):
    """Test OpenLibrary success path."""
    # Mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": "5000"}
    mock_resp.iter_content.return_value = [b"x" * 1500]
    mock_resp.content = b"x" * 1500
    mock_requests_get.return_value.__enter__.return_value = mock_resp

    def fake_optimize(image_bytes: bytes, filepath: str) -> None:
        """Write a placeholder file so the existence check passes."""
        with open(filepath, "wb") as fh:
            fh.write(b"placeholder")

    with patch("app.utils.covers.COVERS_DIR", str(tmp_path)):
        with patch("app.utils.covers.optimize_and_save_image", side_effect=fake_optimize):
            # Patch Image.open used by is_valid_cover to avoid trying to parse fake bytes
            with patch("app.utils.images.Image.open") as mock_image_open:
                mock_img = MagicMock()
                # Make the context manager return a mock image
                mock_image_open.return_value.__enter__.return_value = mock_img

                # Also mock imagehash.phash so the hashing step doesn't try to inspect the fake image
                with patch("app.utils.images.imagehash.phash", return_value=MagicMock()):
                    result = fetch_external_api_cover("9780553380163")

                    assert result is not None
                path, source = result
                assert path == "/static/covers/9780553380163_ol_orig.jpg"
                assert source == "api_openlibrary"
                assert (tmp_path / "9780553380163_ol_orig.jpg").exists()
                # Verify URL
                args, _ = mock_requests_get.call_args
                assert "covers.openlibrary.org" in args[0]


def test_fetch_external_api_cover_failure(mock_requests_get):
    """Test API failure returns None."""
    mock_requests_get.side_effect = requests.RequestException("Connection error")
    path = fetch_external_api_cover("9780553380163")
    assert path is None


def test_generate_cover_cloud_no_key():
    """Test that cloud gen returns None without API key."""
    with patch.dict("os.environ", {}, clear=True):
        path = generate_cover_cloud("123", "Title", "Author", "test-user")
        assert path is None


def test_generate_cover_cloud_success(tmp_path, app):
    """Test OpenAI generation flow."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
        with patch("app.utils.llm_covers.OpenAI") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value.data = [MagicMock(url="http://fake.url/img.jpg")]

            with patch("requests.get") as mock_req:
                mock_req.return_value.status_code = 200
                mock_req.return_value.content = b"image_bytes"

                with (
                    patch("app.utils.llm_covers.COVERS_DIR", str(tmp_path)),
                    patch("app.utils.llm_covers.optimize_and_save_image"),
                    patch("app.utils.llm_covers.record_telemetry"),
                ):
                    result = generate_cover_cloud("123", "Title", "Author", "test-user")
                    assert result is not None
                    path, source = result
                    assert "123_dalle.jpg" in path
                    assert source == "llm_openai"


def test_is_valid_cover_rejects_small_files():
    # 5 bytes is obviously too small for a real JPEG/PNG
    tiny_file = b"12345"
    assert is_valid_cover(tiny_file) is False


def test_is_valid_cover_rejects_corrupt_image():
    # Large enough to pass the size check, but not a valid image
    corrupt_image = b"corrupt_data_" * 300
    assert is_valid_cover(corrupt_image) is False


def test_is_valid_cover_accepts_valid_png_over_1kb():
    """Ensure that a valid PNG payload larger than 1KB is accepted."""
    # Create a simple valid RGB image in memory (larger so the PNG exceeds 1KB)
    image = Image.new("RGB", (512, 512), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    # Sanity check: make sure we satisfy the size requirement
    assert len(image_bytes) > 1024

    # The valid, sufficiently large image should be accepted
    assert is_valid_cover(image_bytes) is True


@patch("app.utils.covers.requests.get")
@patch("app.utils.covers.is_valid_cover")
@patch("app.utils.covers.optimize_and_save_image")
def test_download_direct_url_success(mock_optimize, mock_is_valid, mock_get):
    """Test successful direct URL download."""
    mock_is_valid.return_value = True

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-length": str(MIN_COVER_FILE_SIZE)}
    mock_response.iter_content.return_value = [b"a" * MIN_COVER_FILE_SIZE]
    mock_get.return_value.__enter__.return_value = mock_response

    result = download_direct_url("123456789", "http://example.com/cover.jpg", "api_direct_download")

    assert result is not None
    local_path, source = result
    assert "123456789_ext.jpg" in local_path
    assert source == "api_direct_download"
    mock_optimize.assert_called_once()


@patch("app.utils.covers.requests.get")
def test_download_direct_url_too_large(mock_get):
    """Test rejection of oversized payloads."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Simulate an oversized stream
    mock_response.iter_content.return_value = [b"a" * (MAX_COVER_FILE_SIZE + 10)]
    mock_get.return_value.__enter__.return_value = mock_response

    result = download_direct_url("123456789", "http://example.com/huge.jpg", "api_direct_download")

    assert result is None


@patch("app.utils.covers.requests.get")
def test_download_direct_url_too_small(mock_get):
    """Test rejection of too-small payloads (often 1x1 tracking pixels)."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"a" * (MIN_COVER_FILE_SIZE - 10)]
    mock_get.return_value.__enter__.return_value = mock_response

    result = download_direct_url("123456789", "http://example.com/tiny.jpg", "api_direct_download")

    assert result is None


@patch("app.utils.covers.download_direct_url")
@patch("app.utils.covers.db.session.get")
def test_process_cover_pipeline_intercepts_external_url(mock_db_get, mock_download, app):
    """Test that the pipeline downloads an existing external URL from meta."""
    mock_manifestation = MagicMock(spec=Manifestation)
    mock_manifestation.meta = {"cover_url": "http://discogs.com/cover.jpg"}
    mock_manifestation.isbn13 = None
    mock_db_get.return_value = mock_manifestation

    mock_download.return_value = ("/static/covers/123_ext.jpg", "api_direct_download")

    with app.app_context():
        process_cover_pipeline(
            manifestation_id=1, identifier="123", title="Test", author="Author", llm_permissions={"allow_generate_cover": False}
        )

    mock_download.assert_called_once_with("123", "http://discogs.com/cover.jpg", "api_direct_download")
    assert mock_manifestation.cover_url == "/static/covers/123_ext.jpg"
