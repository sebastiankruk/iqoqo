from unittest.mock import MagicMock, patch

import pytest

from app.utils.covers import fetch_external_api_cover, generate_fallback_cover
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
    mock_resp.iter_content = lambda chunk_size: [b"fake_image_data"]
    mock_requests_get.return_value = mock_resp

    with patch("app.utils.covers.COVERS_DIR", str(tmp_path)):
        path = fetch_external_api_cover("9780123456789")

        assert path == "/static/covers/9780123456789_ol.jpg"
        assert (tmp_path / "9780123456789_ol.jpg").exists()
        # Verify URL
        args, _ = mock_requests_get.call_args
        assert "covers.openlibrary.org" in args[0]


def test_fetch_external_api_cover_failure(mock_requests_get):
    """Test API failure returns None."""
    mock_requests_get.side_effect = Exception("Connection error")
    path = fetch_external_api_cover("0000000000")
    assert path is None


def test_generate_cover_cloud_no_key():
    """Test that cloud gen returns None without API key."""
    with patch.dict("os.environ", {}, clear=True):
        path = generate_cover_cloud("123", "Title", "Author")
        assert path is None


def test_generate_cover_cloud_success(tmp_path):
    """Test OpenAI generation flow."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
        with patch("openai.OpenAI") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.images.generate.return_value.data = [MagicMock(url="http://fake.url/img.jpg")]

            with patch("requests.get") as mock_req:
                mock_req.return_value.status_code = 200
                mock_req.return_value.content = b"image_bytes"

                with patch("app.utils.llm_covers.COVERS_DIR", str(tmp_path)):
                    path = generate_cover_cloud("123", "Title", "Author")
                    assert path is not None
                    assert "123_dalle.jpg" in path
