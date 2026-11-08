"""Tests for LEGO Rebrickable lookup strategy, Fernet encryption, and format normalization."""

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

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.db import db
from app.db.settings import InstanceSettings, is_sensitive_key
from app.strategies.factory import LookupStrategyFactory
from app.strategies.lego import LegoLookupStrategy
from app.utils.rebrickable import (
    fetch_rebrickable_set,
    normalize_set_number,
    search_rebrickable_sets,
)


def test_normalize_set_number():
    """Verify set number normalization converts bare numbers to -1 suffix."""
    assert normalize_set_number("10318") == "10318-1"
    assert normalize_set_number("10318-1") == "10318-1"
    assert normalize_set_number("75192") == "75192-1"
    assert normalize_set_number(" 42115 ") == "42115-1"
    assert normalize_set_number("10318-2") == "10318-2"


def test_rebrickable_api_key_is_sensitive():
    """Verify REBRICKABLE_API_KEY is registered in sensitive keys for Fernet encryption."""
    assert is_sensitive_key("REBRICKABLE_API_KEY") is True


def test_rebrickable_key_encryption_at_rest(app):
    """Verify REBRICKABLE_API_KEY is transparently encrypted at rest in InstanceSettings."""
    with app.app_context():
        test_key = "test_rb_secret_token_abcdef123456"
        InstanceSettings.set_value("REBRICKABLE_API_KEY", test_key)

        # Direct DB query to verify raw value is ciphertext dict (not cleartext)
        stmt = db.select(InstanceSettings).filter_by(key="REBRICKABLE_API_KEY")
        row = db.session.execute(stmt).scalar_one()
        assert row.value != test_key
        assert isinstance(row.value, dict)
        assert row.value.get("_encrypted") is True
        assert row.value["ciphertext"].startswith("gAAAAA")

        # Transparent decryption via get_value
        decrypted = InstanceSettings.get_value("REBRICKABLE_API_KEY")
        assert decrypted == test_key


def test_factory_resolves_lego_strategy():
    """Verify LookupStrategyFactory maps category 'lego' to LegoLookupStrategy."""
    strategy = LookupStrategyFactory.get_strategy("lego")
    assert isinstance(strategy, LegoLookupStrategy)


def test_rebrickable_lookup_by_set_number_success(app):
    """Verify LegoLookupStrategy successfully parses Rebrickable API response."""
    strategy = LegoLookupStrategy()

    mock_set_data = {
        "set_num": "10318-1",
        "name": "Concorde",
        "year": 2023,
        "theme_id": 721,
        "num_parts": 2083,
        "set_img_url": "https://cdn.rebrickable.com/media/sets/10318-1.jpg",
        "set_url": "https://rebrickable.com/sets/10318-1/concorde/",
    }

    mock_set_response = MagicMock(status_code=200)
    mock_set_response.json.return_value = mock_set_data

    mock_theme_response = MagicMock(status_code=200)
    mock_theme_response.json.return_value = {"id": 721, "name": "Icons"}

    mock_minifigs_response = MagicMock(status_code=200)
    mock_minifigs_response.json.return_value = {"count": 0, "results": []}

    def side_effect_get(url, **kwargs):
        if "themes/721" in url:
            return mock_theme_response
        if "minifigs" in url:
            return mock_minifigs_response
        return mock_set_response

    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get", side_effect=side_effect_get):
                result, provider = strategy.lookup("10318")

                assert result is not None
                assert provider == "rebrickable"
                assert result["title"] == "Concorde"
                assert result["set_number"] == "10318-1"
                assert result["piece_count"] == 2083
                assert result["minifig_count"] == 0
                assert result["theme"] == "Icons"
                assert result["category"] == "lego"
                assert result["format"] == "standard_set"
                assert result["cover_url"] == "https://cdn.rebrickable.com/media/sets/10318-1.jpg"
                assert result["_provenance"]["title"] == "rebrickable"
                assert result["_provenance"]["piece_count"] == "rebrickable"


def test_rebrickable_lookup_by_ean_barcode_via_upc(app):
    """Verify scanning an EAN barcode extracts set number via UPC waterfall and queries Rebrickable."""
    strategy = LegoLookupStrategy()

    with app.app_context():
        # 1. Rebrickable direct barcode search returns empty
        mock_empty_search = MagicMock(status_code=200)
        mock_empty_search.json.return_value = {"results": []}

        # 2. UPC waterfall resolves product title with set number '10318'
        upc_resolved = {
            "title": "LEGO Icons Concorde 10318 Building Toy Set",
            "barcode": "5702017416953",
        }

        mock_set_data = {
            "set_num": "10318-1",
            "name": "Concorde",
            "year": 2023,
            "theme_id": 721,
            "num_parts": 2083,
            "set_img_url": "https://cdn.rebrickable.com/media/sets/10318-1.jpg",
            "set_url": "https://rebrickable.com/sets/10318-1/concorde/",
        }
        mock_set_resp = MagicMock(status_code=200)
        mock_set_resp.json.return_value = mock_set_data

        def safe_get_router(url, **kwargs):
            if "search=" in url:
                return mock_empty_search
            return mock_set_resp

        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get", side_effect=safe_get_router):
                with patch("app.strategies.lego.resolve_physical_media", return_value=upc_resolved):
                    result, provider = strategy.lookup("5702017416953")

                    assert result is not None
                    assert provider == "rebrickable"
                    assert result["set_number"] == "10318-1"
                    assert result["barcode"] == "5702017416953"


def test_rebrickable_unconfigured_key_graceful_fallback(app):
    """Verify strategy returns None gracefully without crashing when API key is unset."""
    strategy = LegoLookupStrategy()
    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value=None):
            result, provider = strategy.lookup("10318")
            assert result is None
            assert provider is None


def test_rebrickable_api_404_not_found(app):
    """Verify strategy returns None when Rebrickable returns 404 for an invalid set."""
    strategy = LegoLookupStrategy()
    mock_404 = MagicMock(status_code=404)

    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get", return_value=mock_404):
                result, provider = strategy.lookup("999999")
                assert result is None
                assert provider is None


def test_rebrickable_lookup_candidates(app):
    """Verify lookup_candidates returns structured search results from Rebrickable."""
    strategy = LegoLookupStrategy()
    mock_search_results = {
        "results": [
            {
                "set_num": "75192-1",
                "name": "Millennium Falcon",
                "year": 2017,
                "theme_id": 158,
                "num_parts": 7541,
                "set_img_url": "https://cdn.rebrickable.com/media/sets/75192-1.jpg",
            },
            {
                "set_num": "75257-1",
                "name": "Millennium Falcon",
                "year": 2019,
                "theme_id": 158,
                "num_parts": 1351,
                "set_img_url": "https://cdn.rebrickable.com/media/sets/75257-1.jpg",
            },
        ]
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = mock_search_results

    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get", return_value=mock_resp):
                candidates = strategy.lookup_candidates("Millennium Falcon", max_results=2)
                assert len(candidates) == 2
                assert candidates[0]["set_number"] == "75192-1"
                assert candidates[0]["piece_count"] == 7541
                assert candidates[1]["set_number"] == "75257-1"


def test_rebrickable_rejects_path_traversal_and_invalid_set_syntax(app):
    """Verify fetch_rebrickable_set rejects path traversal attempts without making HTTP requests."""
    from app.utils.rebrickable import fetch_rebrickable_set

    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get") as mock_get:
                assert fetch_rebrickable_set("../../users/profile") is None
                assert fetch_rebrickable_set("10318/../../evil") is None
                assert fetch_rebrickable_set("not-a-number") is None
                # Must not have executed outbound HTTP call for invalid set numbers
                mock_get.assert_not_called()


def test_search_rebrickable_sets_skips_n_plus_one_minifig_calls(app):
    """Verify search_rebrickable_sets does NOT trigger per-candidate _fetch_minifig_count calls."""
    from app.utils.rebrickable import search_rebrickable_sets

    mock_search_results = {
        "results": [
            {
                "set_num": f"1000{i}-1",
                "name": f"Set {i}",
                "year": 2020 + i,
                "theme_id": 1,
                "num_parts": 100 * i,
            }
            for i in range(5)
        ]
    }
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = mock_search_results

    with app.app_context():
        with patch("app.utils.rebrickable.get_rebrickable_api_key", return_value="rb_test_key"):
            with patch("app.utils.rebrickable.safe_get", return_value=mock_resp):
                with patch("app.utils.rebrickable._fetch_minifig_count") as mock_minifigs:
                    candidates = search_rebrickable_sets("Test Sets", max_results=5)
                    assert len(candidates) == 5
                    # Per-candidate minifig queries must be skipped
                    mock_minifigs.assert_not_called()
