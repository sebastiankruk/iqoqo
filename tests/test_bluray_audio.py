"""Tests for the Blu-ray Pure Audio classification boundary.

Pins the Work-driven rule from release-0-7-13:

- A music Work on a Blu-ray carrier → ``music`` / ``bluray_audio``.
- A live-performance Expression on a Blu-ray carrier → ``movie`` / ``bluray``.
- Provider fetchers (Discogs, MusicBrainz) detect BD-Audio carriers and return
  the canonical ``bluray_audio`` format marker.
- The read-time format normalizer resolves BD-Audio raw aliases
  (``Blu-ray Audio``, ``BD-A``, ``BluRay HiFi``, ``Pure Audio Blu-ray``) to
  ``bluray_audio`` via ``shared/format_mappings.yaml``.
"""

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

# pylint: disable=protected-access

from unittest.mock import patch

import pytest

from app.core.format_normalizer import FormatNormalizer, normalize_format
from app.core.taxonomy import FORMAT_TO_CATEGORY, MediaFormat
from app.strategies.audio import (
    BLURAY_AUDIO_RAW_LABELS,
    classify_bluray_carrier,
    is_bluray_audio_release,
    is_bluray_carrier,
)
from app.strategies.video import should_defer_bluray_to_audio
from app.utils.discogs import _normalize_release_data
from app.utils.musicbrainz import _detect_media_format


@pytest.fixture(autouse=True)
def isolated_format_normalizer(monkeypatch, tmp_path):
    """Isolate the format normalizer from the repo YAML (per-test mappings)."""
    import app.core.format_normalizer as mod

    monkeypatch.setattr(mod, "_MAPPINGS_PATH", tmp_path / "dummy.yaml")
    FormatNormalizer.reset()
    yield
    FormatNormalizer.reset()


# ---------------------------------------------------------------------------
# Taxonomy sanity
# ---------------------------------------------------------------------------


class TestBlurayAudioTaxonomy:
    """The canonical format must exist and live under the music category."""

    def test_bluray_audio_constant_exists(self):
        assert MediaFormat.BLURAY_AUDIO == "bluray_audio"
        assert "bluray_audio" in MediaFormat.ALL

    def test_bluray_audio_maps_to_music_category(self):
        assert FORMAT_TO_CATEGORY["bluray_audio"] == "music"


# ---------------------------------------------------------------------------
# Raw-label detectors in app.strategies.audio
# ---------------------------------------------------------------------------


class TestBlurayAudioDetection:
    @pytest.mark.parametrize(
        "label",
        ["Blu-ray Audio", "BD-A", "BluRay HiFi", "Pure Audio Blu-ray", "blu-ray pure audio"],
    )
    def test_known_aliases_detected(self, label):
        assert is_bluray_audio_release([label]) is True

    def test_case_and_whitespace_insensitive(self):
        assert is_bluray_audio_release(["  BLU-RAY AUDIO  "]) is True
        assert is_bluray_audio_release(["bd-a"]) is True

    def test_plain_bluray_is_not_bluray_audio(self):
        # A generic "Blu-ray" label alone does NOT imply Pure Audio —
        # it could be a movie BD.
        assert is_bluray_audio_release(["Blu-ray"]) is False

    def test_plain_bluray_is_still_bluray_carrier(self):
        assert is_bluray_carrier(["Blu-ray"]) is True
        assert is_bluray_carrier(["Blu-ray Audio"]) is True

    def test_cd_and_vinyl_are_not_bluray(self):
        assert is_bluray_audio_release(["CD"]) is False
        assert is_bluray_audio_release(["Vinyl"]) is False
        assert is_bluray_carrier(["CD"]) is False

    def test_empty_and_none(self):
        assert is_bluray_audio_release(None) is False
        assert is_bluray_audio_release([]) is False
        assert is_bluray_carrier(None) is False
        assert is_bluray_carrier([]) is False

    def test_label_set_matches_spec(self):
        # Pin the alias inventory from task 1.1 of release-0-7-13.
        assert {
            "blu-ray audio",
            "bd-a",
            "bluray hifi",
            "pure audio blu-ray",
        }.issubset(BLURAY_AUDIO_RAW_LABELS)


# ---------------------------------------------------------------------------
# Work-driven classification rule
# ---------------------------------------------------------------------------


class TestClassifyBlurayCarrier:
    """The boundary rule: music Work → music/bluray_audio; live performance → movie/bluray."""

    def test_music_work_on_bd_carrier_is_bluray_audio(self):
        assert classify_bluray_carrier("music") == ("music", "bluray_audio")

    def test_music_work_with_studio_expression_is_bluray_audio(self):
        # Studio album = no special expression kind
        assert classify_bluray_carrier("music", None) == ("music", "bluray_audio")
        assert classify_bluray_carrier("music", "studio_album") == ("music", "bluray_audio")

    def test_live_performance_on_bd_carrier_is_movie_bluray(self):
        # A concert BD is a movie-side video manifestation of a Performance Event
        assert classify_bluray_carrier("music", "live_performance") == ("movie", "bluray")
        assert classify_bluray_carrier(None, "live_performance") == ("movie", "bluray")

    def test_non_music_work_defaults_to_movie_bluray(self):
        assert classify_bluray_carrier("movie") == ("movie", "bluray")
        assert classify_bluray_carrier(None) == ("movie", "bluray")
        assert classify_bluray_carrier("text") == ("movie", "bluray")


class TestVideoBoundary:
    """The video strategy must defer BD carriers of music Works to audio."""

    def test_defers_music_work_bd_to_audio(self):
        assert should_defer_bluray_to_audio("music") is True
        assert should_defer_bluray_to_audio("music", "studio_album") is True

    def test_does_not_defer_live_performance(self):
        # Concert BD stays on the video side
        assert should_defer_bluray_to_audio("music", "live_performance") is False
        assert should_defer_bluray_to_audio(None, "live_performance") is False

    def test_does_not_defer_non_music_or_unknown(self):
        assert should_defer_bluray_to_audio("movie") is False
        assert should_defer_bluray_to_audio(None) is False


# ---------------------------------------------------------------------------
# Discogs format detection
# ---------------------------------------------------------------------------


class TestDiscogsBlurayAudio:
    def _release(self, formats):
        return {"title": "Artist - Album", "formats": formats, "id": 1}

    def test_bluray_audio_format_name_detected(self):
        release = self._release([{"name": "Blu-ray", "descriptions": ["Blu-ray Audio"]}])
        assert _normalize_release_data(release)["format"] == "bluray_audio"

    def test_bd_a_description_detected(self):
        release = self._release([{"name": "Blu-ray", "descriptions": ["BD-A"]}])
        assert _normalize_release_data(release)["format"] == "bluray_audio"

    def test_pure_audio_bluray_name_detected(self):
        release = self._release([{"name": "Pure Audio Blu-ray"}])
        assert _normalize_release_data(release)["format"] == "bluray_audio"

    def test_vinyl_still_wins_over_audio_fallback(self):
        release = self._release([{"name": "Vinyl"}])
        assert _normalize_release_data(release)["format"] == "vinyl"

    def test_cd_still_detected(self):
        release = self._release([{"name": "CD"}])
        assert _normalize_release_data(release)["format"] == "cd"

    def test_generic_bluray_video_does_not_match_audio(self):
        # A Blu-ray video release (no audio descriptions) must NOT be
        # classified as bluray_audio by the Discogs audio fetcher.
        release = self._release([{"name": "Blu-ray", "descriptions": ["1080p"]}])
        assert _normalize_release_data(release)["format"] == "audio"


# ---------------------------------------------------------------------------
# MusicBrainz format detection
# ---------------------------------------------------------------------------


class TestMusicBrainzBlurayAudio:
    def test_bluray_medium_maps_to_bluray_audio(self):
        release = {"media": [{"format": "Blu-ray"}]}
        assert _detect_media_format(release) == "bluray_audio"

    def test_bluray_audio_medium_maps_to_bluray_audio(self):
        release = {"media": [{"format": "Blu-ray Audio"}]}
        assert _detect_media_format(release) == "bluray_audio"

    def test_cd_medium_falls_back_to_generic_audio(self):
        release = {"media": [{"format": "CD"}]}
        assert _detect_media_format(release) == "audio"

    def test_missing_media_falls_back_to_generic_audio(self):
        assert _detect_media_format({}) == "audio"
        assert _detect_media_format({"media": []}) == "audio"

    def test_multi_disc_with_bd_detected(self):
        release = {"media": [{"format": "CD"}, {"format": "Blu-ray"}]}
        assert _detect_media_format(release) == "bluray_audio"

    def test_malformed_media_entries_skipped(self):
        release = {"media": ["garbage", None, {"format": "Blu-ray"}]}
        assert _detect_media_format(release) == "bluray_audio"


# ---------------------------------------------------------------------------
# Format normalizer aliases
# ---------------------------------------------------------------------------


class TestBlurayAudioNormalizerAliases:
    """Raw BD-Audio values resolve to bluray_audio via format_mappings.yaml."""

    @pytest.fixture
    def bd_mappings(self, tmp_path, monkeypatch):
        import app.core.format_normalizer as mod

        yaml_path = tmp_path / "format_mappings.yaml"
        yaml_path.write_text(
            "format_normalizations:\n"
            '  "blu-ray audio": bluray_audio\n'
            '  "bd-a": bluray_audio\n'
            '  "bluray hifi": bluray_audio\n'
            '  "pure audio blu-ray": bluray_audio\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_MAPPINGS_PATH", yaml_path)
        FormatNormalizer.reset()
        yield
        FormatNormalizer.reset()

    @pytest.mark.parametrize(
        "raw",
        ["Blu-ray Audio", "BD-A", "BluRay HiFi", "Pure Audio Blu-ray"],
    )
    def test_alias_resolves_to_bluray_audio(self, bd_mappings, raw):
        assert normalize_format(raw, "music") == "bluray_audio"

    def test_alias_is_case_insensitive(self, bd_mappings):
        assert normalize_format("blu-ray audio", "music") == "bluray_audio"
        assert normalize_format("BD-A", "music") == "bluray_audio"

    def test_canonical_bluray_audio_passes_through(self):
        assert normalize_format("bluray_audio", "music") == "bluray_audio"

    def test_bluray_audio_alias_does_not_resolve_to_movie_bluray(self, bd_mappings):
        # Boundary pin: a BD-Audio alias must never collapse into the
        # video-side 'bluray' format.
        assert normalize_format("Blu-ray Audio", "music") != "bluray"


# ---------------------------------------------------------------------------
# End-to-end strategy integration (mocked providers)
# ---------------------------------------------------------------------------


class TestAudioLookupStrategyBlurayAudio:
    def test_discogs_bluray_audio_release_flows_through(self):
        from app.strategies.audio import AudioLookupStrategy

        strategy = AudioLookupStrategy()
        with patch("app.strategies.audio.fetch_discogs_metadata") as mock_fetch:
            mock_fetch.return_value = {
                "title": "A Kind of Blue",
                "author": "Miles Davis",
                "format": "bluray_audio",
            }
            result, provider = strategy.lookup("0602475311353")

            assert provider == "discogs"
            assert result is not None
            assert result["format"] == "bluray_audio"
            # The downstream normalizer treats this as canonical — no rewrite.
            assert normalize_format(result["format"], "music") == "bluray_audio"
