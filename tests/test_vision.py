"""Tests for the vision utility functions."""

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

import json
import os
from unittest.mock import MagicMock, patch

import requests

from app.utils.vision import _extract_via_gemini, _extract_via_ollama, _extract_via_tesseract, extract_metadata_from_cover


@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
@patch.dict(os.environ, {"GEMINI_API_KEY": ""})
def test_extract_waterfall_missing_api_key(mock_tesseract, mock_ollama):
    """Test that missing API key falls back to Ollama and Tesseract."""
    mock_ollama.return_value = None
    mock_tesseract.return_value = None

    result = extract_metadata_from_cover(b"test image")

    assert result is None
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = {"Title": "Dune", "Authors": ["Frank Herbert"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_not_called()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = None
    mock_ollama.return_value = {"Title": "Dune", "Authors": ["Frank Herbert"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_tesseract_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = None
    mock_ollama.return_value = None
    mock_tesseract.return_value = {"Title": "Dune", "Authors": []}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_success(mock_client_class, mock_record, mock_session):
    """Test successful extraction for Gemini."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"Title": "Dune", "Authors": ["Frank Herbert"]}'
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_with_markdown_fences(mock_client_class, mock_record, mock_session):
    """Test successful extraction when model wraps the JSON in markdown code blocks."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '```json\n{"Title": "Dune 2", "Authors": ["Frank Herbert"]}\n```'
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {
        "Title": "Dune 2",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_invalid_json(mock_client_class, mock_record, mock_session):
    """Test handling of invalid JSON response."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "This is not JSON"
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result is None


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("requests.post")
def test_extract_ollama_success(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"Title": "Dune", "Authors": ["Frank Herbert"]}'}
    mock_post.return_value = mock_response

    result = _extract_via_ollama(b"test image")

    assert result == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch.dict("sys.modules", {"pytesseract": MagicMock(), "PIL": MagicMock(), "PIL.Image": MagicMock()})
def test_extract_tesseract_success():
    import sys

    sys.modules["pytesseract"].image_to_string.return_value = "Dune\n\nFrank Herbert"

    result = _extract_via_tesseract(b"test image")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
def test_extract_gemini_blocked_without_cloud_privilege(mock_session):
    """Test that Gemini extraction returns None if user lacks cloud privilege, even with API key."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = False
    mock_session.get.return_value = mock_user

    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        result = _extract_via_gemini(b"test", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")
        assert result is None


def test_parse_authors_comma_separated_string():
    """Test that _parse_json_response splits comma-separated author string."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('{"Title": "Dune", "Authors": "Frank Herbert, Brian Herbert"}')
    assert res == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert", "Brian Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_exception_falls_to_ollama(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an exception in Gemini correctly triggers Ollama."""
    mock_gemini.side_effect = RuntimeError("Gemini is down")
    mock_ollama.return_value = {"Title": "Ollama Result", "Authors": ["Ollama Author"]}

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Ollama Result", "Authors": ["Ollama Author"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_exception_falls_to_tesseract(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an exception in Ollama correctly triggers Tesseract."""
    mock_gemini.return_value = None
    mock_ollama.side_effect = requests.exceptions.RequestException("Ollama connection failed")
    mock_tesseract.return_value = {"Title": "Tesseract Result", "Authors": []}

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Tesseract Result", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_all_exception_returns_none(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that exceptions in all methods result in a None return."""
    mock_gemini.side_effect = RuntimeError("Gemini Error")
    mock_ollama.side_effect = requests.exceptions.RequestException("Ollama Error")
    mock_tesseract.side_effect = RuntimeError("Tesseract Error")

    result = extract_metadata_from_cover(b"test image")

    assert result is None


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_api_error_falls_to_ollama(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that a 3rd party API exception in Gemini correctly triggers Ollama."""

    class FakeAPIError(Exception):
        pass

    mock_gemini.side_effect = FakeAPIError("Gemini API Error")
    mock_ollama.return_value = {"Title": "Ollama Result", "Authors": ["Ollama Author"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Ollama Result", "Authors": ["Ollama Author"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_json_decode_error_falls_to_tesseract(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an invalid JSON response from Ollama falls back to Tesseract."""
    mock_gemini.return_value = None
    mock_ollama.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
    mock_tesseract.return_value = {"Title": "Tesseract Result", "Authors": []}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Tesseract Result", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()
