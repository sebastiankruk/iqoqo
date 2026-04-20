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
from unittest.mock import MagicMock, patch

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
@patch("app.api.scanner.submit_task")
def test_extract_from_cover_success(mock_submit, mock_image_open, client, vision_user_headers):
    """Test successful image content extraction submission."""
    mock_image_open.return_value.verify.return_value = None
    mock_submit.return_value = "test-task-id"

    data = {"cover": (BytesIO(b"dummy_data"), "test.jpg")}
    response = client.post("/api/vision/extract", data=data, content_type="multipart/form-data", headers=vision_user_headers)

    assert response.status_code == 202
    assert response.json["success"] is True
    assert response.json["data"]["task_id"] == "test-task-id"


def test_get_extract_status_not_found(client, vision_user_headers):
    """Test polling for a non-existent task."""
    response = client.get("/api/vision/extract/invalid-id", headers=vision_user_headers)
    # With Celery, unknown IDs default to PENDING (202) until we have a task store
    assert response.status_code == 202
    assert response.json["data"]["status"] == "pending"


@patch("app.api.scanner.get_task_result")
def test_get_extract_status_processing(mock_get_result, client, vision_user_headers):
    """Test polling for a task that is still processing."""
    mock_get_result.return_value = {"status": "processing"}
    response = client.get("/api/vision/extract/test-id", headers=vision_user_headers)
    assert response.status_code == 202
    assert response.json["data"]["status"] == "processing"


@patch("app.api.scanner.get_task_result")
def test_get_extract_status_completed(mock_get_result, client, vision_user_headers):
    """Test polling for a completed task."""
    mock_get_result.return_value = {"status": "completed", "result": {"Title": "Dune", "Authors": ["Frank Herbert"]}}
    response = client.get("/api/vision/extract/test-id", headers=vision_user_headers)
    assert response.status_code == 200
    assert response.json["data"]["Title"] == "Dune"
    assert response.json["data"]["Authors"] == ["Frank Herbert"]


@patch("app.api.scanner.get_task_result")
def test_get_extract_status_failed(mock_get_result, client, vision_user_headers):
    """Test polling for a failed task."""
    mock_get_result.return_value = {"status": "failed", "error": "Gemini API error"}
    response = client.get("/api/vision/extract/test-id", headers=vision_user_headers)
    assert response.status_code == 500
    assert response.json["error"] == "Gemini API error"


# Note: test_extract_from_cover_failure is removed as failure now happens during polling or background processing.


def test_extract_from_cover_oversized_header(client, vision_user_headers):
    """Reject early if Content-Length header exceeds limit (413)."""
    from unittest.mock import PropertyMock

    with patch("flask.Request.content_length", new_callable=PropertyMock) as mock_cl:
        mock_cl.return_value = _MAX_COVER_SIZE + 1

        response = client.post(
            "/api/vision/extract",
            data={"cover": (BytesIO(b"small"), "test.jpg")},
            content_type="multipart/form-data",
            headers=vision_user_headers,
        )

        assert response.status_code == 413
        assert "File too large" in response.json["error"]


@patch("app.api.scanner.Image.open")
def test_extract_from_cover_pil_verify_failure(mock_image_open, client, vision_user_headers):
    """Reject if PIL.Image.verify fails (corrupt image)."""
    mock_img = MagicMock()
    mock_img.verify.side_effect = OSError("Corrupt image")
    mock_image_open.return_value = mock_img

    data = {"cover": (BytesIO(b"corrupt data"), "test.jpg")}
    response = client.post(
        "/api/vision/extract",
        data=data,
        content_type="multipart/form-data",
        headers=vision_user_headers,
    )
    assert response.status_code == 400
    assert "Invalid or corrupted image file" in response.json["error"]


# =====================================================================
# UNIFIED BARCODE LOOKUP API TESTS
# =====================================================================


@patch("app.api.scanner.fetch_isbn_metadata")
@patch("app.api.scanner.fetch_discogs_metadata")
def test_lookup_barcode_book_isbn(mock_discogs, mock_isbn, client, normal_user_headers):
    """Test looking up a standard 13-digit ISBN correctly bypasses audio fetchers."""
    # Ensure it normalizes key as well
    mock_isbn.return_value = {"Title": "Neuromancer", "Format": "book"}

    # 978 prefix guarantees book routing
    response = client.get("/api/lookup/9780441013593", headers=normal_user_headers)

    assert response.status_code == 200
    # Scanner ensures title overrides Title
    assert response.json["data"]["title"] == "Neuromancer"
    mock_isbn.assert_called_once()
    mock_discogs.assert_not_called()


@patch("app.api.scanner.fetch_isbn_metadata")
@patch("app.api.scanner.fetch_discogs_metadata")
def test_lookup_barcode_audio_upc(mock_discogs, mock_isbn, client, normal_user_headers):
    """Test looking up a standard 12-digit UPC uses audio fetchers first and normalizes payload keys."""
    # Simulating raw API keys that typically break frontend rendering
    mock_discogs.return_value = {"Title": "Kind of Blue", "Format": "audio", "artist": "Miles Davis", "thumb": "http://img.png"}

    response = client.get("/api/lookup/074646493524", headers=normal_user_headers)

    assert response.status_code == 200

    # Asserting scanner.py successfully mapped keys
    assert response.json["data"]["title"] == "Kind of Blue"
    assert response.json["data"]["author"] == "Miles Davis"
    assert response.json["data"]["cover_url"] == "http://img.png"

    mock_discogs.assert_called_once()


# =====================================================================
# UNIFIED SCAN INGESTION API TESTS
# =====================================================================


@patch("app.api.scanner.IngestService.ingest_audio_from_barcode")
def test_scan_barcode_creates_audio_item(mock_ingest_audio, client, normal_user_headers, app):
    """Test scan endpoint correctly processes audio format hint."""
    mock_manifestation = MagicMock()
    mock_manifestation.id = 999
    mock_manifestation.title = "Dark Side of the Moon"
    mock_manifestation.meta = {"title": "Dark Side of the Moon"}
    mock_ingest_audio.return_value = mock_manifestation

    payload = {"barcode": "077774600125", "format": "audio"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)

    assert response.status_code == 201
    assert response.json["data"]["manifestation_id"] == 999
    assert response.json["data"]["title"] == "Dark Side of the Moon"
    mock_ingest_audio.assert_called_once_with("077774600125")


@patch("app.api.scanner.IngestService.ingest_from_isbn")
def test_scan_barcode_creates_book_item(mock_ingest_book, client, normal_user_headers, app):
    """Test scan endpoint correctly processes book format hint."""
    mock_manifestation = MagicMock()
    mock_manifestation.id = 888
    mock_manifestation.title = "Dune"
    mock_manifestation.meta = {"title": "Dune"}
    mock_ingest_book.return_value = mock_manifestation

    payload = {"barcode": "9780441013593", "format": "book"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)

    assert response.status_code == 201
    assert response.json["data"]["manifestation_id"] == 888
    assert response.json["data"]["title"] == "Dune"
    mock_ingest_book.assert_called_once_with("9780441013593")


@patch("app.api.scanner.resolve_physical_media")
@patch("app.api.scanner.fetch_video_metadata")
def test_lookup_barcode_video_tmdb(mock_tmdb, mock_upc, client, normal_user_headers):
    """Test looking up video format."""
    mock_upc.return_value = None
    mock_tmdb.return_value = {"Title": "The Matrix", "Format": "video"}
    response = client.get("/api/lookup/12345?format=video", headers=normal_user_headers)

    assert response.status_code == 200
    assert response.json["data"]["title"] == "The Matrix"
    mock_tmdb.assert_called_once()


@patch("app.api.scanner.resolve_physical_media")
@patch("app.api.scanner.fetch_video_metadata")
def test_lookup_title_video_tmdb(mock_tmdb, mock_upc, client, normal_user_headers):
    """Test looking up video format by title directly."""
    mock_tmdb.return_value = {"Title": "The Lord of the Rings", "Format": "video"}
    mock_upc.return_value = None  # Mock UPC miss

    response = client.get("/api/lookup/The%20Lord%20of%20the%20Rings?format=video", headers=normal_user_headers)

    assert response.status_code == 200
    assert response.json["data"]["title"] == "The Lord of the Rings"
    # Should be called with the decoded string
    mock_tmdb.assert_called_with("The Lord of the Rings")


@patch("app.api.scanner.resolve_physical_media")
@patch("app.api.scanner.fetch_bgg_metadata")
def test_lookup_barcode_boardgame_bgg(mock_bgg, mock_resolve, client, normal_user_headers):
    """Test looking up game format."""
    mock_resolve.return_value = {"title": "Catan", "barcode": "54321"}
    mock_bgg.return_value = {"Title": "Catan", "title": "Catan", "Format": "boardgame"}
    response = client.get("/api/lookup/54321?format=game", headers=normal_user_headers)

    assert response.status_code == 200
    assert response.json["data"]["title"] == "Catan"
    mock_bgg.assert_called_once()
    mock_resolve.assert_called_once()


@patch("app.api.scanner.IngestService.ingest_video_from_barcode")
def test_scan_barcode_creates_video_item(mock_ingest_video, client, normal_user_headers, app):
    """Test scan endpoint correctly processes video format hint."""
    mock_manifestation = MagicMock()
    mock_manifestation.id = 777
    mock_manifestation.title = "The Matrix"
    mock_manifestation.meta = {"title": "The Matrix"}
    mock_ingest_video.return_value = mock_manifestation

    payload = {"barcode": "0123456789", "format": "video"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)

    assert response.status_code == 201
    assert response.json["data"]["manifestation_id"] == 777
    mock_ingest_video.assert_called_once_with("0123456789")


@patch("app.api.scanner.IngestService.ingest_game_from_barcode")
def test_scan_barcode_creates_game_item(mock_ingest_game, client, normal_user_headers, app):
    """Test scan endpoint correctly processes boardgame format hint."""
    mock_manifestation = MagicMock()
    mock_manifestation.id = 666
    mock_manifestation.title = "Catan"
    mock_manifestation.meta = {"title": "Catan"}
    mock_ingest_game.return_value = mock_manifestation

    payload = {"barcode": "9876543210", "format": "boardgame"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)

    assert response.status_code == 201
    assert response.json["data"]["manifestation_id"] == 666
    mock_ingest_game.assert_called_once_with("9876543210")


@patch("app.api.scanner.resolve_physical_media")
@patch("app.api.scanner.fetch_video_metadata")
def test_lookup_video_fallback_to_upc_meta(mock_tmdb, mock_upc, client, normal_user_headers):
    """Test that if TMDB fails, we still return the Allegro/UPC metadata."""
    upc_payload = {"title": "Allegro Item", "cover_url": "http://img.jpg", "source": "Allegro Listing"}
    mock_upc.return_value = upc_payload
    mock_tmdb.return_value = None  # TMDB finds nothing

    response = client.get("/api/lookup/5906619071187?format=video", headers=normal_user_headers)

    assert response.status_code == 200
    assert response.json["data"]["title"] == "Allegro Item"
    assert response.json["data"]["source"] == "Allegro Listing"


@patch("app.api.scanner.resolve_physical_media")
@patch("app.api.scanner.fetch_video_metadata")
def test_lookup_format_injection(mock_tmdb, mock_upc, client, normal_user_headers):
    """Test that format key is injected for frontend normalization."""
    mock_upc.return_value = {"title": "No Format Item"}
    mock_tmdb.return_value = None

    response = client.get("/api/lookup/12345?format=video", headers=normal_user_headers)

    assert response.status_code == 200
    assert response.json["data"]["format"] == "video"
