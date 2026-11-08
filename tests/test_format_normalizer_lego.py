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
"""Tests for LEGO and construction set format normalization."""

import pytest

from app.core.format_normalizer import (
    FormatNormalizer,
    expand_format_filter,
    normalize_format,
)
from app.core.taxonomy import MediaCategory, MediaFormat


@pytest.fixture(autouse=True)
def reset_normalizer():
    """Reset the normalizer's cached mappings before each test."""
    FormatNormalizer.reset()
    yield
    FormatNormalizer.reset()


class TestLegoCanonicalPassThrough:
    """Canonical LEGO format values pass through unchanged."""

    @pytest.mark.parametrize(
        "fmt",
        [
            MediaFormat.STANDARD_SET,
            MediaFormat.UCS_COLLECTOR_SET,
            MediaFormat.TECHNIC_SET,
            MediaFormat.MINIFIGURE_SERIES,
            MediaFormat.POLYBAG,
            MediaFormat.MODULAR_BUILDING,
            MediaFormat.UNKNOWN_LEGO,
        ],
    )
    def test_canonical_lego_formats_pass_through(self, fmt: str):
        assert normalize_format(fmt) == fmt
        assert FormatNormalizer.is_canonical(fmt) is True


class TestLegoFormatMappings:
    """Non-canonical LEGO format aliases resolve to canonical targets."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("lego_set", MediaFormat.STANDARD_SET),
            ("lego", MediaFormat.STANDARD_SET),
            ("set", MediaFormat.STANDARD_SET),
            ("ucs", MediaFormat.UCS_COLLECTOR_SET),
            ("technic", MediaFormat.TECHNIC_SET),
            ("cmf", MediaFormat.MINIFIGURE_SERIES),
            ("minifigures", MediaFormat.MINIFIGURE_SERIES),
            ("minifigure", MediaFormat.MINIFIGURE_SERIES),
        ],
    )
    def test_lego_aliases_resolve_correctly(self, raw: str, expected: str):
        assert normalize_format(raw) == expected

    def test_null_format_with_lego_content_type(self):
        """NULL format with content_type='lego' resolves to standard_set via mappings."""
        assert normalize_format(None, content_type=MediaCategory.LEGO) == MediaFormat.STANDARD_SET

    def test_unknown_raw_with_lego_content_type_fallback(self, monkeypatch, tmp_path):
        """When user mapping is absent, unknown format with lego category resolves to unknown_lego."""
        dummy_yaml = tmp_path / "empty_mappings.yaml"
        dummy_yaml.write_text("format_normalizations:\n", encoding="utf-8")
        import app.core.format_normalizer as mod

        monkeypatch.setattr(mod, "_MAPPINGS_PATH", dummy_yaml)
        FormatNormalizer.reset()

        assert normalize_format("totally_unknown_custom_brick", content_type=MediaCategory.LEGO) == MediaFormat.UNKNOWN_LEGO
        assert normalize_format(None, content_type=MediaCategory.LEGO) == MediaFormat.UNKNOWN_LEGO
        assert normalize_format("mystery_box", content_type=MediaCategory.BOARD_GAME) == MediaFormat.UNKNOWN_BOARD_GAME
        assert normalize_format("mystery_pieces", content_type=MediaCategory.PUZZLE) == MediaFormat.UNKNOWN_PUZZLE
        assert normalize_format("mystery_audio", content_type=MediaCategory.AUDIOBOOK) == MediaFormat.UNKNOWN_AUDIOBOOK


class TestLegoExpandFormatFilter:
    """expand_format_filter expands canonical LEGO formats to include raw aliases."""

    def test_expand_standard_set_filter(self):
        expanded = expand_format_filter([MediaFormat.STANDARD_SET])
        assert expanded is not None
        assert MediaFormat.STANDARD_SET in expanded
        assert "lego_set" in expanded
        assert "lego" in expanded
        assert "set" in expanded

    def test_expand_ucs_filter(self):
        expanded = expand_format_filter([MediaFormat.UCS_COLLECTOR_SET])
        assert expanded is not None
        assert MediaFormat.UCS_COLLECTOR_SET in expanded
        assert "ucs" in expanded
