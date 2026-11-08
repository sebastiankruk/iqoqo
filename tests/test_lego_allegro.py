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

"""Unit and API tests for LEGO lookup via Allegro fallback, Rebrickable integration, and format normalization."""

from unittest.mock import patch

from app.api.scanner import _normalize_preview_meta
from app.db import db
from app.db.core import MediaCategory, MediaFormat
from app.db.models import Manifestation
from app.strategies.lego import LegoLookupStrategy
from app.utils.allegro import _extract_allegro_parameters


def test_lego_lookup_allegro_fallback_success() -> None:
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
        assert meta["format"] == "standard_set"


def test_lego_lookup_candidates_combines_rebrickable_and_allegro() -> None:
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
        assert candidates[1]["format"] == "standard_set"


def test_extract_allegro_parameters_lego_fields() -> None:
    """Verify _extract_allegro_parameters extracts LEGO set number, piece count, and theme."""
    raw_params = [
        {"name": "EAN", "values": ["5702018068229"]},
        {"name": "Numer produktu", "values": ["77256"]},
        {"name": "Liczba elementów", "values": ["290 szt."]},
        {"name": "Seria", "valuesLabels": ["Speed Champions"]},
        {"name": "Producent", "valuesLabels": ["LEGO"]},
    ]
    extracted = _extract_allegro_parameters(raw_params)

    assert extracted["barcode"] == "5702018068229"
    assert extracted["set_number"] == "77256"
    assert extracted["piece_count"] == 290
    assert extracted["theme"] == "Speed Champions"
    assert extracted["publisher"] == "LEGO"


def test_normalize_preview_meta_maps_lego_format_hint_to_standard_set() -> None:
    """Verify _normalize_preview_meta maps format_hint='lego' to standard_set instead of BOOK."""
    meta = {"title": "LEGO Speed Champions 77256 Wehikuł czasu z Powrotu do przyszłości"}
    normalized = _normalize_preview_meta(meta, format_hint="lego")

    assert normalized["format"] == MediaFormat.STANDARD_SET


def test_scanner_lookup_lego_barcode_auto_saves_as_lego_category(client, normal_user_headers) -> None:
    """Verify GET /api/lookup/<barcode>?format=lego auto-saves manifestation under LEGO category, not book."""
    barcode = "5702018068229"
    allegro_mock_data = {
        "title": "LEGO Speed Champions 77256 Wehikuł czasu z Powrotu do przyszłości",
        "barcode": barcode,
        "cover_url": "https://a.allegroimg.com/s1024/lego-77256.jpg",
        "publisher": "LEGO",
        "set_number": "77256",
        "piece_count": 290,
        "theme": "Speed Champions",
        "data_source": "allegro",
    }

    with (
        patch("app.strategies.lego.search_rebrickable_sets", return_value=[]),
        patch("app.strategies.lego.fetch_allegro_metadata", return_value=allegro_mock_data),
        patch("app.strategies.lego.fetch_rebrickable_set", return_value=None),
        patch("app.core.ingest.start_cover_processing"),
    ):
        resp = client.get(f"/api/lookup/{barcode}?format=lego", headers=normal_user_headers)
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["success"] is True
        data = payload["data"]
        assert data["format"] == "standard_set"
        assert data["category"] == "lego"
        assert data["set_number"] == "77256"
        assert data["manifestation_id"] is not None

        saved = db.session.get(Manifestation, data["manifestation_id"])
        assert saved is not None
        assert saved.format == "standard_set"
        assert saved.expression.content_type == MediaCategory.LEGO
