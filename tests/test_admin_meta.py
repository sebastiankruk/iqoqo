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
"""Tests for FRBR metadata sanitization and parsing helpers."""

import json

from app.utils.json_utils import parse_meta, sanitize_meta


def test_sanitize_meta_empty():
    """Test sanitization with None or empty dictionary."""
    assert sanitize_meta(None) is None
    assert not sanitize_meta({})


def test_sanitize_meta_conversion():
    """Test that dicts and lists are converted to JSON strings, but primitives remain."""
    input_meta = {
        "string_val": "hello",
        "int_val": 42,
        "dict_val": {"nested": "value"},
        "list_val": [1, 2, 3],
    }

    result = sanitize_meta(input_meta)

    assert result["string_val"] == "hello"
    assert result["int_val"] == 42
    assert result["dict_val"] == json.dumps({"nested": "value"})
    assert result["list_val"] == json.dumps([1, 2, 3])


def test_parse_meta_empty():
    """Test parsing with None or empty dictionary."""
    assert parse_meta(None) is None
    assert not parse_meta({})


def test_parse_meta_conversion():
    """Test that valid JSON strings are parsed, and non-JSON strings/primitives are untouched."""
    input_meta = {
        "string_val": "hello",
        "int_val": 42,
        "dict_string": '{"nested": "value"}',
        "list_string": "[1, 2, 3]",
        "invalid_json": '{"bad": "json"',  # Missing closing brace
    }

    result = parse_meta(input_meta)

    assert result["string_val"] == "hello"
    assert result["int_val"] == 42
    assert result["dict_string"] == {"nested": "value"}
    assert result["list_string"] == [1, 2, 3]
    assert result["invalid_json"] == '{"bad": "json"'  # Invalid JSON returned as-is


def test_parse_meta_type_error():
    """Test that TypeError during json.loads is handled gracefully."""
    input_meta = {
        "whitespace_only": "   ",
    }
    result = parse_meta(input_meta)
    assert result["whitespace_only"] == "   "  # Whitespace-only string returned as-is


def test_parse_meta_numeric_strings_preserved():
    """Test that numeric-looking strings are NOT coerced (leading zeros, etc.)."""
    input_meta = {
        "zero_padded": "00123",
        "bool_string": "true",
        "float_string": "3.14",
    }

    result = parse_meta(input_meta)

    assert result["zero_padded"] == "00123"
    assert result["bool_string"] == "true"
    assert result["float_string"] == "3.14"
