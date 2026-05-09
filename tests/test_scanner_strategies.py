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
"""Tests for the Scanner Lookup Strategy Factory & Implementations."""

from unittest.mock import MagicMock, patch

import pytest

from app.strategies.lookup import (
    AudioLookupStrategy,
    BoardGameLookupStrategy,
    BookLookupStrategy,
    DefaultFallbackStrategy,
    LookupStrategyFactory,
    VideoLookupStrategy,
)


def test_strategy_factory_resolves_correctly():
    """Ensure the factory hands out the specific format Strategy classes."""
    assert isinstance(LookupStrategyFactory.get_strategy("movie"), VideoLookupStrategy)
    assert isinstance(LookupStrategyFactory.get_strategy("music"), AudioLookupStrategy)
    assert isinstance(LookupStrategyFactory.get_strategy("book"), BookLookupStrategy)
    assert isinstance(LookupStrategyFactory.get_strategy("board_game"), BoardGameLookupStrategy)
    assert isinstance(LookupStrategyFactory.get_strategy("unknown_hint"), DefaultFallbackStrategy)
    assert isinstance(LookupStrategyFactory.get_strategy(None), DefaultFallbackStrategy)


@patch("app.strategies.lookup.resolve_physical_media")
@patch("app.strategies.lookup.fetch_video_metadata")
def test_video_strategy_lookup(mock_fetch, mock_resolve):
    strategy = VideoLookupStrategy()
    mock_resolve.return_value = {"title": "The Matrix"}
    mock_fetch.return_value = {"Title": "The Matrix", "year": 1999}

    meta, provider = strategy.lookup("12345")

    assert provider == "tmdb"
    assert meta["Title"] == "The Matrix"
    assert meta["data_source"] == "tmdb"


@patch("app.strategies.lookup.canonicalize_isbn")
@patch("app.strategies.lookup.fetch_isbn_metadata")
def test_book_strategy_lookup(mock_fetch, mock_canonical):
    strategy = BookLookupStrategy()
    mock_canonical.return_value = "9781234567890"
    mock_fetch.return_value = {"Title": "Dune", "Source": "Google Books"}

    meta, provider = strategy.lookup("9781234567890")

    assert provider == "isbn"
    assert meta["Title"] == "Dune"
    assert meta["data_source"] == "google_books"
