"""
Tests for the refactored Scanner Strategy Pattern mapping to FRBR models.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from unittest.mock import patch

import pytest
import requests

from app.strategies.boardgame import BoardGameLookupStrategy

# Adapting imports based on Phase 1 Refactoring
from app.strategies.book import BookLookupStrategy


def test_book_lookup_strategy_success():
    """Ensure BookLookupStrategy correctly aggregates valid provider data."""
    strategy = BookLookupStrategy()
    with patch("app.strategies.book.fetch_isbn_metadata") as mock_fetch:
        mock_fetch.return_value = {"title": "Dune", "author": "Frank Herbert", "isbn": "9780441172719"}
        result, provider = strategy.lookup("9780441172719")

        assert result is not None
        assert result["title"] == "Dune"
        assert provider == "isbn"
        mock_fetch.assert_called_once()


def test_book_lookup_strategy_provider_failure():
    """Ensure strategy handles provider timeouts and enforces standard API error format."""
    strategy = BookLookupStrategy()
    with patch("app.strategies.book.fetch_isbn_metadata", side_effect=requests.RequestException("API Timeout")):
        with patch("app.strategies.book.fetch_discogs_metadata", return_value=None):
            with patch("app.strategies.book.fetch_audio_metadata", return_value=None):
                result, _ = strategy.lookup("9780441172719")
                assert result is None


def test_game_lookup_strategy_success():
    """Ensure GameLookupStrategy correctly fetches and structures Board Game metadata."""
    strategy = BoardGameLookupStrategy()
    with patch("app.strategies.boardgame.fetch_bgg_metadata") as mock_fetch:
        mock_fetch.return_value = {"title": "Catan", "min_players": 3}
        result, provider = strategy.lookup("123456")  # Short numeric triggers BGG

        assert result is not None
        assert result["title"] == "Catan"
        assert provider == "bgg"
        mock_fetch.assert_called_once()


def test_audio_lookup_strategy():
    """AudioLookupStrategy delegates to Discogs fetcher for short numeric barcode."""
    from app.strategies.audio import AudioLookupStrategy

    strategy = AudioLookupStrategy()
    with patch("app.strategies.audio.fetch_discogs_by_id") as mock_discogs_by_id:
        mock_discogs_by_id.return_value = {"title": "Dark Side of the Moon", "data_source": "discogs"}
        result, provider = strategy.lookup("12345")

        assert result is not None
        assert result["title"] == "Dark Side of the Moon"
        assert provider == "discogs"
        mock_discogs_by_id.assert_called_once()


def test_video_lookup_strategy():
    """VideoLookupStrategy delegates to TMDB fetcher via resolve_physical_media."""
    from app.strategies.video import VideoLookupStrategy

    strategy = VideoLookupStrategy()
    with patch("app.strategies.video.resolve_physical_media") as mock_upc:
        mock_upc.return_value = {"title": "The Matrix", "media_type": "Blu-ray"}
        with patch("app.strategies.video.fetch_video_metadata") as mock_tmdb:
            mock_tmdb.return_value = {"title": "The Matrix", "data_source": "tmdb", "release_date": "1999"}
            result, provider = strategy.lookup("883929312517")

            assert result is not None
            assert result["title"] == "The Matrix"
            assert provider == "tmdb"
            assert result.get("data_source") == "tmdb"


def test_default_fallback_strategy_isbn_13():
    """DefaultFallbackStrategy prioritizes ISBN lookup for 13-digit 978/979 barcodes."""
    from app.strategies.default import DefaultFallbackStrategy

    strategy = DefaultFallbackStrategy()
    with patch("app.strategies.default.fetch_isbn_metadata") as mock_isbn:
        mock_isbn.return_value = {"title": "Neuromancer", "Source": "google_books"}
        result, provider = strategy.lookup("9780441569595")
        assert result is not None
        assert provider == "isbn"
        assert result["title"] == "Neuromancer"
        mock_isbn.assert_called_once()


def test_default_fallback_strategy_isbn_10():
    """DefaultFallbackStrategy recognizes valid 10-digit ISBNs."""
    from app.strategies.default import DefaultFallbackStrategy

    strategy = DefaultFallbackStrategy()
    with patch("app.strategies.default.fetch_isbn_metadata") as mock_isbn:
        mock_isbn.return_value = {"title": "Neuromancer", "Source": "google_books"}
        result, provider = strategy.lookup("0441569595")
        assert result is not None
        assert provider == "isbn"
        mock_isbn.assert_called_once()


def test_default_fallback_strategy_non_isbn_10_char():
    """DefaultFallbackStrategy does not falsely fast-path arbitrary 10-character barcodes as ISBN."""
    from app.strategies.default import DefaultFallbackStrategy

    strategy = DefaultFallbackStrategy()
    with (
        patch("app.strategies.default.fetch_isbn_metadata") as mock_isbn,
        patch("app.strategies.default.fetch_discogs_metadata") as mock_discogs,
    ):
        mock_discogs.return_value = {"title": "Discovery", "data_source": "discogs"}
        result, provider = strategy.lookup("ABCDEFGHIJ")
        # Should not have called ISBN fetcher
        mock_isbn.assert_not_called()
        assert result is not None
        assert provider == "discogs"
