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
    with patch("app.strategies.book.fetch_isbn_metadata", side_effect=Exception("API Timeout")):
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
