"""Tests for the format normalizer module."""

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

# pylint: disable=redefined-outer-name,protected-access

import pytest

from app.core.format_normalizer import (
    FormatNormalizer,
    expand_format_filter,
    normalize_format,
    normalize_format_counts,
)


@pytest.fixture(autouse=True)
def isolated_format_normalizer(monkeypatch, tmp_path):
    import app.core.format_normalizer as mod

    monkeypatch.setattr(mod, "_MAPPINGS_PATH", tmp_path / "dummy.yaml")
    FormatNormalizer.reset()
    yield
    FormatNormalizer.reset()


@pytest.fixture(autouse=True)
def reset_normalizer():
    """Reset the normalizer's cached mappings before each test."""
    FormatNormalizer.reset()


# ---------------------------------------------------------------------------
# 8.1: Unit tests for normalize_format / FormatNormalizer
# ---------------------------------------------------------------------------


class TestCanonicalPassThrough:
    """Canonical format values pass through unchanged."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("dvd", "dvd"),
            ("vinyl", "vinyl"),
            ("board_game", "board_game"),
            ("bluray", "bluray"),
            ("4k_uhd", "4k_uhd"),
            ("book", "book"),
            ("cd", "cd"),
            ("cards", "cards"),
        ],
    )
    def test_canonical_passes_through(self, raw, expected):
        assert normalize_format(raw) == expected

    def test_canonical_unknown_video(self):
        assert normalize_format("unknown_video") == "unknown_video"

    def test_canonical_unknown_audio(self):
        assert normalize_format("unknown_audio") == "unknown_audio"

    def test_canonical_unknown_text(self):
        assert normalize_format("unknown_text") == "unknown_text"


class TestUserMappingResolution:
    """Non-canonical values resolved via user-defined mappings."""

    def test_exact_mapping_video_to_dvd(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text(
            "format_normalizations:\n  video: dvd\n  audio: cd\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format("video", "movie") == "dvd"
        assert normalize_format("audio", "music") == "cd"

    def test_case_insensitive_mapping(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text(
            "format_normalizations:\n  Video: dvd\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format("Video", "movie") == "dvd"
        assert normalize_format("video", "movie") == "dvd"


class TestNullFormatResolution:
    """NULL format values resolved with content-type-scoped mappings."""

    def test_null_mapped_via_content_type(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text(
            "format_normalizations:\n  null:\n    movie: dvd\n    music: cd\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format(None, "movie") == "dvd"
        assert normalize_format(None, "music") == "cd"

    def test_null_without_mapping_falls_to_unknown(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("format_normalizations: {}\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format(None, "movie") == "unknown_video"
        assert normalize_format(None, "music") == "unknown_audio"
        assert normalize_format(None, "text") == "unknown_text"
        assert normalize_format(None, None) == "unknown_text"


class TestFallbackResolution:
    """Non-canonical values without user mapping fall back to unknown_* placeholders."""

    def test_video_falls_to_unknown_video(self):
        # "video" has FORMAT_ALIAS_TO_CATEGORY → movie → unknown_video
        assert normalize_format("video") == "unknown_video"

    def test_audio_falls_to_unknown_audio(self):
        assert normalize_format("audio") == "unknown_audio"

    def test_boardgame_falls_to_unknown_board_game_category(self):
        # "boardgame" → board_game category, but no specific unknown_board_game format
        # Since there's no unknown_board_game, it falls through to the alias category
        result = normalize_format("boardgame")
        # boardgame → board_game category → FORMAT_TO_CATEGORY lookup for unknown
        # The _category_to_unknown_placeholder maps "board_game" → None,
        # so ultimate fallback is unknown_text
        assert result in ("unknown_text", "board_game")

    def test_completely_unrecognized_ultimate_fallback(self):
        assert normalize_format("xyz123", None) == "unknown_text"

    def test_with_content_type_fallback(self):
        result = normalize_format("xyz123", "movie")
        # "xyz123" not in aliases, not in mappings, not canonical
        # Step 4: FORMAT_ALIAS_TO_CATEGORY.get("xyz123") is None
        # Step 5: use content_type "movie" → unknown_video
        assert result == "unknown_video"


class TestIdempotency:
    """Normalizer is idempotent — applying twice yields same result."""

    def test_canonical_twice(self):
        assert normalize_format("dvd", "movie") == "dvd"
        assert normalize_format("dvd", "movie") == "dvd"

    def test_mapped_then_canonical_twice(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("format_normalizations:\n  video: dvd\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        first = normalize_format("video", "movie")
        second = normalize_format(first, "movie")
        assert first == "dvd"
        assert second == "dvd"

    def test_null_mapped_twice(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("format_normalizations:\n  null:\n    movie: dvd\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        first = normalize_format(None, "movie")
        second = normalize_format(first, "movie")
        assert first == "dvd"
        assert second == "dvd"


class TestIsCanonical:
    """is_canonical() helper."""

    def test_known_canonical_returns_true(self):
        assert FormatNormalizer.is_canonical("dvd") is True
        assert FormatNormalizer.is_canonical("bluray") is True
        assert FormatNormalizer.is_canonical("unknown_video") is True

    def test_non_canonical_returns_false(self):
        assert FormatNormalizer.is_canonical("video") is False
        assert FormatNormalizer.is_canonical(None) is False
        assert FormatNormalizer.is_canonical("xyz") is False


# ---------------------------------------------------------------------------
# 8.2: Tests with empty / missing format_mappings.yaml
# ---------------------------------------------------------------------------


class TestMissingMappingFile:
    """Normalizer works correctly when format_mappings.yaml is missing."""

    def test_normalize_without_mapping_file(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        nonexistent = tmp_path / "nonexistent_mappings.yaml"
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", nonexistent)
        FormatNormalizer.reset()

        # Canonical still passes through
        assert normalize_format("dvd") == "dvd"
        # Non-canonical falls to unknown
        assert normalize_format("video") == "unknown_video"
        # NULL falls to unknown
        assert normalize_format(None, "movie") == "unknown_video"

    def test_empty_mapping_file(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format("dvd") == "dvd"
        assert normalize_format("video") == "unknown_video"

    def test_no_normalizations_key(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("other_key: value\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        assert normalize_format("video") == "unknown_video"


class TestInvalidMappingTarget:
    """Invalid mapping targets are logged and ignored."""

    def test_invalid_target_ignored(self, tmp_path, monkeypatch, caplog):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text(
            "format_normalizations:\n  video: nonexistent_format\n  audio: cd\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        import logging

        with caplog.at_level(logging.WARNING):
            assert normalize_format("video") == "unknown_video"
            assert normalize_format("audio") == "cd"

        assert any("nonexistent_format" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 8.1+: Expand format filter tests
# ---------------------------------------------------------------------------


class TestExpandFormatFilter:
    """expand_format_filter() resolves canonical filters to include raw keys."""

    def test_none_returns_none(self):
        assert expand_format_filter(None) is None

    def test_canonical_passes_through(self):
        result = expand_format_filter(["dvd", "bluray"])
        assert "dvd" in result
        assert "bluray" in result

    def test_expands_mapped_raw_values(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("format_normalizations:\n  video: dvd\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        result = expand_format_filter(["dvd"])
        assert "dvd" in result
        assert "video" in result  # mapped raw key

    def test_unknown_video_includes_itself(self):
        result = expand_format_filter(["unknown_video"])
        assert "unknown_video" in result


# ---------------------------------------------------------------------------
# 8.1+: Normalize format counts tests
# ---------------------------------------------------------------------------


class TestNormalizeFormatCounts:
    """normalize_format_counts() merges counts by canonical format."""

    def test_merges_counts_for_normalized_formats(self):
        raw = {"video": 3, "dvd": 2, "bluray": 1}
        # "video" → unknown_video (no mapping), "dvd" → dvd, "bluray" → bluray
        result = normalize_format_counts(raw)
        assert result.get("dvd", 0) == 2
        assert result.get("bluray", 0) == 1
        # "video" normalizes to unknown_video
        assert result.get("unknown_video", 0) == 3

    def test_merges_mapped_values(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text("format_normalizations:\n  video: dvd\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()

        raw = {"video": 3, "dvd": 2}
        result = normalize_format_counts(raw)
        # both "video" and "dvd" normalize to "dvd"
        assert result.get("dvd", 0) == 5

    def test_empty_input(self):
        result = normalize_format_counts({})
        assert not result


# ---------------------------------------------------------------------------
# 8.5: Frontend format badge label tests
# (backend validation that unknown_* resolve to correct labels via taxonomy)
# ---------------------------------------------------------------------------


class TestUnknownFormatLabels:
    """Verify unknown_* formats resolve to correct categories."""

    def test_unknown_video_in_movie_category(self):
        from app.core.taxonomy import FORMAT_TO_CATEGORY, MediaFormat

        assert FORMAT_TO_CATEGORY.get(MediaFormat.UNKNOWN_VIDEO) == "movie"

    def test_unknown_audio_in_music_category(self):
        from app.core.taxonomy import FORMAT_TO_CATEGORY, MediaFormat

        assert FORMAT_TO_CATEGORY.get(MediaFormat.UNKNOWN_AUDIO) == "music"

    def test_unknown_text_in_text_category(self):
        from app.core.taxonomy import FORMAT_TO_CATEGORY, MediaFormat

        assert FORMAT_TO_CATEGORY.get(MediaFormat.UNKNOWN_TEXT) == "text"

    def test_unknown_formats_in_media_formats(self):
        from app.core.taxonomy import MediaFormat

        assert "unknown_video" in MediaFormat.ALL
        assert "unknown_audio" in MediaFormat.ALL
        assert "unknown_text" in MediaFormat.ALL
