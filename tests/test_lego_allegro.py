# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Unit tests for LEGO lookup via Allegro fallback and Rebrickable integration."""

from unittest.mock import MagicMock, patch

from app.strategies.lego import LegoLookupStrategy


def test_lego_lookup_allegro_fallback_success():
    """Verify that scanning a LEGO EAN barcode falls back to Allegro when Rebrickable returns nothing."""
    barcode = "5702018068229"
    allegro_mock_data = {
        "title": "LEGO Icons 10318 Concorde",
        "barcode": barcode,
        "cover_url": "https://a.allegroimg.com/s1024/lego-concorde.jpg",
        "publisher": "LEGO",
        "set_number": "10318",
        "piece_count": 2083,
        "theme": "LEGO Icons",
        "data_source": "allegro",
    }

    with (
        patch("app.strategies.lego.search_rebrickable_sets", return_value=[]),
        patch("app.strategies.lego.fetch_allegro_metadata", return_value=allegro_mock_data) as mock_allegro,
        patch("app.strategies.lego.fetch_rebrickable_set", return_value={"minifig_count": 0, "piece_count": 2083}),
    ):
        strategy = LegoLookupStrategy()
        meta, provider = strategy.lookup(barcode)

        mock_allegro.assert_called_once_with(barcode)
        assert provider == "allegro"
        assert meta is not None
        assert meta["title"] == "LEGO Icons 10318 Concorde"
        assert meta["set_number"] == "10318"
        assert meta["piece_count"] == 2083
        assert meta["category"] == "lego"
        assert meta["format"] == "construction_set"


def test_lego_lookup_candidates_combines_rebrickable_and_allegro():
    """Verify that lookup_candidates queries Allegro when Rebrickable has fewer than max_results."""
    query = "LEGO Concorde"
    reb_candidates = [{"title": "Concorde", "set_number": "10318-1", "piece_count": 2083}]
    allegro_candidates = [{"title": "LEGO 10318 Samolot Concorde", "barcode": "5702018068229"}]

    with (
        patch("app.strategies.lego.search_rebrickable_sets", return_value=reb_candidates),
        patch("app.strategies.lego.fetch_allegro_candidates", return_value=allegro_candidates),
    ):
        strategy = LegoLookupStrategy()
        candidates = strategy.lookup_candidates(query, max_results=5)

        assert len(candidates) == 2
        assert candidates[0]["title"] == "Concorde"
        assert candidates[1]["title"] == "LEGO 10318 Samolot Concorde"
        assert candidates[1]["data_source"] == "allegro"
        assert candidates[1]["category"] == "lego"
