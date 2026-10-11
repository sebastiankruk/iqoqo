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
"""Tests for multi-provider metadata and cover gap-filling (OpenSpec change multi-provider-gap-fill-v084)."""

import time
from unittest.mock import MagicMock, patch

import pytest
from rdflib import PROV, URIRef

from app.core.frbr_service import build_collection_rdf_graph
from app.core.ingest import IngestService
from app.db.models import Manifestation
from app.utils.isbn import (
    ISBNProviderOutcome,
    ISBNProviderOutcomeStatus,
    _merge_metadata_gaps,
    fetch_isbn_metadata,
)


def test_merge_metadata_gaps_preserves_primary_and_tracks_provenance():
    primary = {
        "Title": "Primary Title",
        "Authors": ["Primary Author"],
        "Description": "Primary Description",
        "publisher": None,
        "cover_url": None,
    }
    secondary = {
        "Title": "Secondary Title",
        "Authors": ["Secondary Author"],
        "publisher": "Acme Publishing",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780123456789-L.jpg",
        "publication_date": "2024",
    }

    merged = _merge_metadata_gaps(primary, secondary, "google_books", "open_library")

    assert merged["Title"] == "Primary Title"
    assert merged["Authors"] == ["Primary Author"]
    assert merged["Description"] == "Primary Description"
    assert merged["publisher"] == "Acme Publishing"
    assert merged["cover_url"] == "https://covers.openlibrary.org/b/isbn/9780123456789-L.jpg"
    assert merged["publication_date"] == "2024"

    prov = merged.get("_provenance")
    assert prov is not None
    assert prov["Title"] == "google_books"
    assert prov["Authors"] == "google_books"
    assert prov["Description"] == "google_books"
    assert prov["publisher"] == "open_library"
    assert prov["cover_url"] == "open_library"
    assert prov["publication_date"] == "open_library"


def test_fetch_isbn_metadata_triggers_gap_fill_when_cover_missing():
    gb_metadata = {
        "Title": "Dune",
        "Authors": ["Frank Herbert"],
        "Description": "Epic sci-fi novel",
        "cover_url": None,
        "Source": "Google Books",
    }
    ol_metadata = {
        "Title": "Dune (OpenLibrary)",
        "Authors": ["Frank Herbert"],
        "cover_url": "https://covers.openlibrary.org/b/id/12345-L.jpg",
        "publisher": "Chilton Books",
        "Source": "Open Library",
    }

    gb_outcome = ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata=gb_metadata,
        provider="google_books",
    )
    ol_outcome = ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata=ol_metadata,
        provider="open_library",
    )

    with (
        patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_outcome),
        patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_outcome),
    ):
        result = fetch_isbn_metadata("9780441172719")

    assert result is not None
    assert result["Title"] == "Dune"
    assert result["cover_url"] == "https://covers.openlibrary.org/b/id/12345-L.jpg"
    assert result["publisher"] == "Chilton Books"
    assert result["_provenance"]["Title"] == "google_books"
    assert result["_provenance"]["cover_url"] == "open_library"


def test_fetch_isbn_metadata_timeout_ceiling_aborts_secondary():
    gb_metadata = {
        "Title": "Dune",
        "Authors": ["Frank Herbert"],
        "cover_url": None,
    }
    gb_outcome = ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata=gb_metadata,
        provider="google_books",
    )

    def slow_ol_outcome(isbn):
        time.sleep(0.1)
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata={"cover_url": "https://covers.openlibrary.org/slow.jpg"},
            provider="open_library",
        )

    with (
        patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_outcome),
        patch("app.utils.isbn._lookup_open_library_outcome", side_effect=slow_ol_outcome) as mock_ol,
    ):
        # Setting max_duration to 0.0 forces immediate timeout before secondary
        result = fetch_isbn_metadata("9780441172719", max_duration=0.0)

    assert result is not None
    assert result["Title"] == "Dune"
    assert result.get("cover_url") is None
    mock_ol.assert_not_called()


def test_rdf_serialization_outputs_multiple_prov_triples_for_multi_provider():
    item_dict = {
        "id": 101,
        "manifestation_id": 101,
        "title": "Dune",
        "isbn": "9780441172719",
        "cover_url": "https://covers.openlibrary.org/b/id/12345-L.jpg",
        "_provenance": {
            "title": "google_books",
            "cover_url": "open_library",
        },
    }

    g = build_collection_rdf_graph([item_dict], base_url="https://iqoqo.test")

    m_uri = URIRef("https://iqoqo.test/manifestations/101")
    prov_triples = list(g.triples((m_uri, PROV.wasDerivedFrom, None)))

    assert len(prov_triples) == 2
    prov_targets = {str(target) for _, _, target in prov_triples}
    assert any("google" in t for t in prov_targets)
    assert any("openlibrary" in t for t in prov_targets)


def test_end_to_end_manifestation_ingest_with_gap_fill(app):
    with app.app_context():
        isbn = "9780441172719"
        gb_metadata = {
            "Title": "Dune",
            "Authors": ["Frank Herbert"],
            "Description": "Sandworms and spice",
            "cover_url": None,
            "Source": "Google Books",
        }
        ol_metadata = {
            "Title": "Dune Alternate",
            "Authors": ["Frank Herbert"],
            "cover_url": "https://covers.openlibrary.org/b/id/12345-L.jpg",
            "publisher": "Chilton Books",
            "Source": "Open Library",
        }

        gb_outcome = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata=gb_metadata,
            provider="google_books",
        )
        ol_outcome = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata=ol_metadata,
            provider="open_library",
        )

        with (
            patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_outcome),
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_outcome),
            patch("app.core.ingest.start_cover_processing") as mock_start_cover,
        ):
            manifestation = IngestService.ingest_from_isbn(isbn)

        assert manifestation is not None
        assert manifestation.meta["title"] == "Dune"
        assert manifestation.meta["cover_url"] == "https://covers.openlibrary.org/b/id/12345-L.jpg"
        assert manifestation.meta["publisher"] == "Chilton Books"
        assert manifestation.meta["_provenance"]["cover_url"] == "open_library"
        assert manifestation.meta["_provenance"]["Title"] == "google_books"
        mock_start_cover.assert_called_once()
