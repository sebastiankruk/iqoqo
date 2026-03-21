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

import os
from unittest.mock import MagicMock, patch

from app.utils.vision import extract_metadata_from_cover


@patch.dict(os.environ, {"GEMINI_API_KEY": ""})
def test_extract_missing_api_key():
    """Test that missing API key returns None."""
    result = extract_metadata_from_cover(b"test image")
    assert result is None


@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client")
def test_extract_success(mock_client_class):
    """Test successful extraction."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"Title": "Dune", "Authors": ["Frank Herbert"]}'
    mock_client.models.generate_content.return_value = mock_response

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}


@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client")
def test_extract_with_markdown_fences(mock_client_class):
    """Test successful extraction when model wraps the JSON in markdown code blocks."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '```json\n{"Title": "Dune 2", "Authors": ["Frank Herbert"]}\n```'
    mock_client.models.generate_content.return_value = mock_response

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Dune 2", "Authors": ["Frank Herbert"]}


@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client")
def test_extract_invalid_json(mock_client_class):
    """Test handling of invalid JSON response."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "This is not JSON"
    mock_client.models.generate_content.return_value = mock_response

    result = extract_metadata_from_cover(b"test image")

    assert result is None
