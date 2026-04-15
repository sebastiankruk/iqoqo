"""Tests for FRBR metadata sanitization and parsing helpers."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import json

from app.utils.json_utils import parse_meta, sanitize_meta


def test_sanitize_meta_empty():
    """Test sanitization with None or empty dictionary."""
    assert sanitize_meta(None) is None
    assert sanitize_meta({}) == {}


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
    assert parse_meta({}) == {}


def test_parse_meta_conversion():
    """Test that valid JSON strings are parsed, and invalid strings/primitives are untouched."""
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
    assert result["invalid_json"] == '{"bad": "json"'


def test_parse_meta_type_error():
    """Test that non-container valid JSON strings remain as strings."""
    input_meta = {"strange_string": "1"}  # Valid JSON primitive, but not a container
    result = parse_meta(input_meta)
    assert result["strange_string"] == "1"


def test_parse_meta_non_container_string_unchanged():
    """Plain strings that are not JSON containers must not be coerced."""
    result = parse_meta({"plain": "hello world", "numeric_str": "00123"})
    assert result["plain"] == "hello world"
    assert result["numeric_str"] == "00123"  # Must NOT become integer 123
