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
    assert sanitize_meta({}) == {}  # pylint: disable=use-implicit-booleaness-not-comparison


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
    assert parse_meta({}) == {}  # pylint: disable=use-implicit-booleaness-not-comparison


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


def test_parse_meta_array_field_single_author():
    """Single author string should be converted to array."""
    result = parse_meta({"authors": "Remigiusz Mróz"})
    assert result == {"authors": ["Remigiusz Mróz"]}


def test_parse_meta_array_field_comma_separated():
    """Comma-separated authors should be split into array."""
    result = parse_meta({"authors": "Author1, Author2, Author3"})
    assert result == {"authors": ["Author1", "Author2", "Author3"]}


def test_parse_meta_array_field_semicolon_separated():
    """Semicolon-separated authors should be split into array."""
    result = parse_meta({"authors": "Author1; Author2"})
    assert result == {"authors": ["Author1", "Author2"]}


def test_parse_meta_array_field_empty_string():
    """Empty string for array field should become empty array."""
    result = parse_meta({"authors": ""})
    assert result == {"authors": []}


def test_parse_meta_array_field_whitespace_only():
    """Whitespace-only string for array field should become empty array."""
    result = parse_meta({"authors": "   "})
    assert result == {"authors": []}


def test_parse_meta_array_field_already_array():
    """Array values should be preserved."""
    result = parse_meta({"authors": ["Author1", "Author2"]})
    assert result == {"authors": ["Author1", "Author2"]}


def test_parse_meta_array_field_json_string():
    """JSON string arrays should be parsed."""
    result = parse_meta({"authors": '["Author1", "Author2"]'})
    assert result == {"authors": ["Author1", "Author2"]}


def test_parse_meta_array_field_null():
    """Null value for array field should become empty array."""
    result = parse_meta({"authors": None})
    assert result == {"authors": []}


def test_parse_meta_array_field_trims_whitespace():
    """Whitespace should be trimmed from each array element."""
    result = parse_meta({"authors": "  Author1  ,  Author2  "})
    assert result == {"authors": ["Author1", "Author2"]}


def test_parse_meta_array_field_filters_empty():
    """Empty entries should be filtered out."""
    result = parse_meta({"authors": "Author1,,Author2,"})
    assert result == {"authors": ["Author1", "Author2"]}


def test_parse_meta_array_field_tags():
    """Tags field should also be normalized to array."""
    result = parse_meta({"tags": "fiction, sci-fi, adventure"})
    assert result == {"tags": ["fiction", "sci-fi", "adventure"]}


def test_parse_meta_array_field_genres():
    """Genres field should be normalized to array."""
    result = parse_meta({"genres": "Thriller, Mystery"})
    assert result == {"genres": ["Thriller", "Mystery"]}


def test_parse_meta_non_array_field_unchanged():
    """Non-array fields should remain as strings."""
    result = parse_meta({"title": "Some Title", "isbn13": "978-3-16-148410-0"})
    assert result == {"title": "Some Title", "isbn13": "978-3-16-148410-0"}


def test_parse_meta_mixed_fields():
    """Mixed array and non-array fields should be handled correctly."""
    result = parse_meta({"authors": "Author1, Author2", "title": "Some Title", "tags": "fiction, thriller", "isbn13": "978-3-16-148410-0"})
    assert result == {
        "authors": ["Author1", "Author2"],
        "title": "Some Title",
        "tags": ["fiction", "thriller"],
        "isbn13": "978-3-16-148410-0",
    }
