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
"""Tests for C132 Modulo-11 ISSN validation, GS1 977 parsing, cover OCR, and SerialLookupStrategy."""

from unittest.mock import MagicMock

import pytest
import requests

from app.strategies.factory import LookupStrategyFactory
from app.strategies.serials import SerialLookupStrategy
from app.utils.issn import is_977_periodical_barcode, is_valid_issn, normalize_issn, parse_cover_issue_label, parse_issn_or_977
from app.utils.vision import _parse_json_response


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1507-5966", "1507-5966"),
        ("ISSN 15075966", "1507-5966"),
        ("0027-9358", "0027-9358"),
        ("0028-0836", "0028-0836"),
        ("2049-3630", "2049-3630"),
        ("0378-5955", "0378-5955"),
        ("1507-5969", None),  # invalid Modulo-11 check digit
        ("123", None),
    ],
)
def test_issn_modulo11_validation_and_normalization(raw, expected):
    """Validate and normalize ISSNs using Modulo-11 check digits."""
    assert normalize_issn(raw) == expected
    assert is_valid_issn(raw) is (expected is not None)


@pytest.mark.parametrize(
    "barcode,expected_ean,expected_addon,expected_hint",
    [
        ("977150759603711", "9771507596037", "11", 11),  # 11(50)/2003
        ("977150759604407", "9771507596044", "07", 7),  # 7(58)/2004
        ("977150759604412", "9771507596044", "12", 12),  # 12(63)/2004
        ("977150759650101", "9771507596501", "01", 1),  # 1(64)/2005
        ("977150759650106", "9771507596501", "06", 6),  # 6(69)/2005
        ("9771507596044", "9771507596044", None, None),  # bare 13-digit 977
    ],
)
def test_parse_national_geographic_polska_977_barcodes(barcode, expected_ean, expected_addon, expected_hint):
    """All 5 real National Geographic Polska 977 barcodes reconstruct ISSN 1507-5966 and extract EAN-2."""
    assert is_977_periodical_barcode(barcode)
    parsed = parse_issn_or_977(barcode)
    assert parsed is not None
    assert parsed["kind"] == "ean977"
    assert parsed["issn"] == "1507-5966"
    assert parsed["ean"] == expected_ean
    assert parsed["ean_addon"] == expected_addon
    assert parsed["addon_issue_hint"] == expected_hint
    assert parsed["full_barcode"] == (barcode if expected_addon else None)


@pytest.mark.parametrize(
    "text,exp_issue,exp_cum,exp_month,exp_year",
    [
        ("NR 11(50) LISTOPAD 2003 ISSN 1507-5966 INDEKS 323357", "11", 50, 11, 2003),
        ("NR 7(58) LIPIEC 2004 ISSN 1507-5966", "7", 58, 7, 2004),
        ("NR 12(63) GRUDZIEŃ 2004", "12", 63, 12, 2004),
        ("NR 1(64) STYCZEŃ 2005", "1", 64, 1, 2005),
        ("NR 6(69) CZERWIEC 2005", "6", 69, 6, 2005),
        ("Issue 4(102) July 2024", "4", 102, 7, 2024),
    ],
)
def test_parse_cover_issue_label_multilingual(text, exp_issue, exp_cum, exp_month, exp_year):
    """Extract issue number, cumulative number, PL/EN month, year, ISSN, and Indeks."""
    parsed = parse_cover_issue_label(text)
    assert parsed["issue_number"] == exp_issue
    assert parsed["cumulative_issue_number"] == exp_cum
    assert parsed["publication_month"] == exp_month
    assert parsed["publication_year"] == exp_year


def test_vision_parse_json_response_includes_serial_fields():
    """Vision JSON response parser preserves serial cover fields cleanly."""
    raw = (
        '{"Title": "National Geographic Polska", "Publisher": "G+J RBA", '
        '"ISSN": "1507-5966", "Indeks": "323357", "IssueNumber": "7", '
        '"CumulativeIssueNumber": "58", "PublicationMonth": "7", "PublicationYear": "2004", '
        '"CoverHeadline": "Skarby pod lodem"}'
    )
    parsed = _parse_json_response(raw)
    assert parsed is not None
    assert parsed["Title"] == "National Geographic Polska"
    assert parsed["issn"] == "1507-5966"
    assert parsed["indeks"] == "323357"
    assert parsed["issue_number"] == "7"
    assert parsed["cumulative_issue_number"] == 58
    assert parsed["publication_month"] == 7
    assert parsed["publication_year"] == 2004
    assert parsed["cover_headline"] == "Skarby pod lodem"


def test_serial_lookup_strategy_waterfall_and_factory(monkeypatch):
    """Verify factory resolution and Biblioteka Narodowa -> Crossref -> graceful fallback."""
    strategy = LookupStrategyFactory.get_strategy("magazine")
    assert isinstance(strategy, SerialLookupStrategy)

    bn_resp = MagicMock()
    bn_resp.status_code = 200
    bn_resp.json.return_value = {
        "bibs": [
            {
                "title": "National Geographic Polska /",
                "publisher": "G+J RBA,",
                "language": "pol",
            }
        ]
    }
    monkeypatch.setattr("app.strategies.serials.safe_get", lambda *args, **kwargs: bn_resp)

    meta, provider = strategy.lookup("977150759604407")
    assert provider == "biblioteka_narodowa"
    assert meta is not None
    assert meta["title"] == "National Geographic Polska"
    assert meta["publisher"] == "G+J RBA"
    assert meta["issn"] == "1507-5966"
    assert meta["ean"] == "9771507596044"
    assert meta["ean_addon"] == "07"
    assert meta["full_barcode"] == "977150759604407"
    assert meta["issue_number"] == "7"

    # Graceful failure without fabricating fake titles/covers
    monkeypatch.setattr(
        "app.strategies.serials.safe_get",
        MagicMock(side_effect=requests.Timeout("timed out")),
    )
    monkeypatch.setattr("app.strategies.serials.fetch_allegro_metadata", lambda *_a, **_kw: None)
    failed_meta, failed_provider = strategy.lookup("977150759604407")
    assert failed_meta is None
    assert failed_provider is None


def test_bn_lookup_uses_isbn_issn_param_verifies_marc_022_and_extracts_marc_245(monkeypatch):
    """BN lookup queries isbnIssn + kind=czasopismo, rejects 022$y spin-offs/books, and cleans MARC 245."""
    captured_params = {}
    bn_resp = MagicMock()
    bn_resp.status_code = 200
    bn_resp.json.return_value = {
        "bibs": [
            {
                "title": "Matka Teresa : miłość w czynach /",
                "isbnIssn": "8871351460",
                "kind": "książka",
                "publisher": "Wydawnictwo Velar",
            },
            {
                "title": "National Geographic Traveler /",
                "isbnIssn": "2545-3521",
                "kind": "czasopismo",
                "marc": {
                    "fields": [
                        {"022": {"subfields": [{"a": "2545-3521"}, {"y": "1507-5966"}]}},
                        {"245": {"subfields": [{"a": "National Geographic Traveler"}]}},
                    ]
                },
            },
            {
                "title": "Natl. Geogr. (Wyd. pol.) National Geographic. Polska /",
                "isbnIssn": "1507-5966",
                "kind": "czasopismo",
                "language": "pol",
                "marc": {
                    "fields": [
                        {"022": {"subfields": [{"a": "1507-5966"}]}},
                        {"245": {"subfields": [{"a": "National Geographic."}, {"p": "Polska /"}]}},
                        {"260": {"subfields": [{"b": "Wydawnictwo G+J RBA,"}]}},
                    ]
                },
            },
        ]
    }

    def fake_safe_get(_url, params=None, **_kwargs):
        captured_params.update(params or {})
        return bn_resp

    monkeypatch.setattr("app.strategies.serials.safe_get", fake_safe_get)
    meta, provider = SerialLookupStrategy().lookup("9771507596044")
    assert provider == "biblioteka_narodowa"
    assert captured_params.get("isbnIssn") == "1507-5966"
    assert captured_params.get("kind") == "czasopismo"
    assert meta is not None
    assert meta["title"] == "National Geographic Polska"
    assert meta["publisher"] == "Wydawnictwo G+J RBA"


@pytest.mark.parametrize(
    "ocr_text,exp_issn,exp_issue,exp_cum,exp_month,exp_year,exp_addon",
    [
        ("Cena 14,95 zt ne 11(50) LISTOPAD 2003 9 771507 596037 11>", "1507-5966", "11", 50, 11, 2003, "11"),
        ("Cena 9,90 7% vat) RMo12(63) GRUDZIEN 2004 9 771507 596044 12>", "1507-5966", "12", 63, 12, 2004, "12"),
        ("Jak zmieni sie klimat? RMo12(63) GRUDZIEN 2004 ISSN 1507-5966", "1507-5966", "12", 63, 12, 2004, None),
        ("ISSN 1507-5966 INDEKS 323357 07>", "1507-5966", "7", None, None, None, "07"),
    ],
)
def test_parse_cover_issue_label_handles_garbled_ocr_and_977_addon(ocr_text, exp_issn, exp_issue, exp_cum, exp_month, exp_year, exp_addon):
    """OCR-garbled NR prefixes, spaced 977 EANs, and 07>/11>/12> add-ons are recovered."""
    parsed = parse_cover_issue_label(ocr_text)
    assert parsed.get("issn") == exp_issn
    assert parsed.get("issue_number") == exp_issue
    assert parsed.get("cumulative_issue_number") == exp_cum
    assert parsed.get("publication_month") == exp_month
    assert parsed.get("publication_year") == exp_year
    assert parsed.get("ean_addon") == exp_addon
