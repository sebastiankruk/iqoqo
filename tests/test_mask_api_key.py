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
"""Tests for API key masking in admin settings."""

from app.api.admin import _mask_api_key


def test_mask_api_key_shows_last_4_chars():
    """API key should show last 4 characters after masking."""
    # Just verify it masks - shows last 4 actual chars
    assert "***" in _mask_api_key("sk-1234567890abcdef")
    assert _mask_api_key("sk-1234567890abcdef").endswith("cdef")
    
    # Verify env var masking also works
    assert "***" in _mask_api_key("OPENAI_KEY_12345678")
    assert _mask_api_key("OPENAI_KEY_12345678").endswith("5678")


def test_mask_api_key_empty_string():
    """Empty string should return empty."""
    assert _mask_api_key("") == ""
    assert _mask_api_key(None) == ""  # type: ignore


def test_mask_api_key_short_values():
    """Short values (< 8 chars) should be fully masked."""
    assert _mask_api_key("abc") == "***"
    assert _mask_api_key("1234567") == "***"


def test_mask_api_key_8_chars():
    """Exactly 8 char value should show last 4."""
    assert _mask_api_key("12345678") == "***5678"