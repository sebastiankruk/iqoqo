"""Tests for the scanner API endpoints."""

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

from io import BytesIO
from unittest.mock import patch

from app.api.scanner import _MAX_COVER_SIZE


def test_extract_from_cover_no_file(client, vision_user_headers):
    """Test extraction with no file provided."""
    response = client.post("/api/vision/extract", headers=vision_user_headers)
    assert response.status_code == 400
    assert response.json["error"] == "No file provided"


def test_extract_from_cover_forbidden(client, normal_user_headers):
    """Test extraction returns 403 for user without LLM_GENERATE_METADATA."""
    response = client.post("/api/vision/extract", headers=normal_user_headers)
    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_extract_from_cover_invalid_ext(client, vision_user_headers):
    """Test extraction with an invalid file extension."""
    data = {"cover": (BytesIO(b"dummy_data"), "test.txt")}
    response = client.post("/api/vision/extract", data=data, content_type="multipart/form-data", headers=vision_user_headers)
    assert response.status_code == 400
    assert "Invalid file type" in response.json["error"]


def test_read_bounded_within_limit():
    """_read_bounded returns bytes when payload is within the limit."""
    from app.api.scanner import _read_bounded

    payload = b"hello"
    assert _read_bounded(BytesIO(payload), len(payload)) == payload


def test_read_bounded_exact_limit():
    """_read_bounded returns bytes when payload is exactly at the limit."""
    from app.api.scanner import _read_bounded

    payload = b"x" * _MAX_COVER_SIZE
    assert _read_bounded(BytesIO(payload), _MAX_COVER_SIZE) == payload


def test_read_bounded_over_limit():
    """_read_bounded returns None when payload exceeds the limit by one byte."""
    from app.api.scanner import _read_bounded

    payload = b"x" * (_MAX_COVER_SIZE + 1)
    assert _read_bounded(BytesIO(payload), _MAX_COVER_SIZE) is None


def test_extract_from_cover_oversized_body(client, vision_user_headers):
    """Reject when actual payload exceeds limit even without a Content-Length header (413)."""
    oversized_payload = b"x" * (_MAX_COVER_SIZE + 1)
    data = {"cover": (BytesIO(oversized_payload), "test.jpg")}
    response = client.post(
        "/api/vision/extract",
        data=data,
        content_type="multipart/form-data",
        headers=vision_user_headers,
    )
    assert response.status_code == 413
    assert "File too large" in response.json["error"]


@patch("app.api.scanner.Image.open")
def test_extract_from_cover_invalid_image(mock_image_open, client, vision_user_headers):
    """Test extraction with a corrupt image file."""
    mock_image_open.side_effect = SyntaxError()
    data = {"cover": (BytesIO(b"dummy_data"), "test.jpg")}
    response = client.post("/api/vision/extract", data=data, content_type="multipart/form-data", headers=vision_user_headers)
    assert response.status_code == 400
    assert "Invalid or corrupted image file" in response.json["error"]


@patch("app.api.scanner.Image.open")
@patch("app.api.scanner.extract_metadata_from_cover")
def test_extract_from_cover_success(mock_extract, mock_image_open, client, vision_user_headers):
    """Test successful image content extraction."""
    mock_image_open.return_value.verify.return_value = None
    mock_extract.return_value = {"Title": "Dune", "Authors": ["Frank Herbert"]}

    data = {"cover": (BytesIO(b"dummy_data"), "test.jpg")}
    response = client.post("/api/vision/extract", data=data, content_type="multipart/form-data", headers=vision_user_headers)

    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["Title"] == "Dune"
    assert response.json["data"]["Authors"] == ["Frank Herbert"]


@patch("app.api.scanner.Image.open")
@patch("app.api.scanner.extract_metadata_from_cover")
def test_extract_from_cover_failure(mock_extract, mock_image_open, client, vision_user_headers):
    """Test missing or failing vision extraction."""
    mock_image_open.return_value.verify.return_value = None
    mock_extract.return_value = None

    data = {"cover": (BytesIO(b"dummy_data"), "test.jpg")}
    response = client.post("/api/vision/extract", data=data, content_type="multipart/form-data", headers=vision_user_headers)

    assert response.status_code == 503
    assert "Vision extraction failed. All fallback methods" in response.json["error"]
