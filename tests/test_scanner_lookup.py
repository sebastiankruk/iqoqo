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

"""Tests for multi-candidate title lookup and disambiguation in scanner and lookup strategies."""

from unittest.mock import MagicMock, patch

from app.strategies.book import BookLookupStrategy
from app.utils.allegro import fetch_allegro_candidates
from app.utils.isbn import fetch_google_books_candidates


def test_fetch_google_books_candidates_returns_multiple():
    """Verify Google Books candidate search parses multiple candidates without truncation."""
    mock_gb_response = {
        "totalItems": 5,
        "items": [
            {
                "volumeInfo": {
                    "title": "Jaś i Małgosia - Wydanie 1",
                    "authors": ["Bracia Grimm"],
                    "description": "Klasyczna baśń",
                    "imageLinks": {"thumbnail": "http://img.books/1.jpg"},
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780441172719"}],
                }
            },
            {
                "volumeInfo": {
                    "title": "Jaś i Małgosia - Wydanie 2",
                    "authors": ["Jan Brzechwa"],
                    "description": "Wierszowana wersja",
                    "imageLinks": {"thumbnail": "http://img.books/2.jpg"},
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780441013593"}],
                }
            },
            {
                "volumeInfo": {
                    "title": "Jaś i Małgosia - Wydanie Ilustrowane",
                    "authors": ["Wilhelm Grimm", "Jacob Grimm"],
                    "description": "Pięknie ilustrowana",
                    "imageLinks": {"thumbnail": "http://img.books/3.jpg"},
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780553380163"}],
                }
            },
            {
                "volumeInfo": {
                    "title": "Jaś i Małgosia - Audiobook",
                    "authors": ["Bracia Grimm"],
                    "description": "Czyta Piotr Fronczewski",
                    "imageLinks": {"thumbnail": "http://img.books/4.jpg"},
                }
            },
        ],
    }

    with patch("app.utils.isbn._make_session") as mock_session_factory:
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gb_response
        mock_session.get.return_value = mock_resp
        mock_session_factory.return_value = mock_session

        candidates = fetch_google_books_candidates("Jaś i Małgosia", max_results=10)

        assert len(candidates) == 4
        assert candidates[0]["Title"] == "Jaś i Małgosia - Wydanie 1"
        assert candidates[0]["barcode"] == "9780441172719"
        assert candidates[0]["cover_url"] == "http://img.books/1.jpg"
        assert candidates[1]["Title"] == "Jaś i Małgosia - Wydanie 2"
        assert candidates[2]["Title"] == "Jaś i Małgosia - Wydanie Ilustrowane"
        assert candidates[3]["Title"] == "Jaś i Małgosia - Audiobook"


def test_fetch_allegro_candidates_returns_multiple():
    """Verify Allegro candidate search returns multiple products from catalog."""
    mock_allegro_products = {
        "products": [
            {
                "name": "Jaś i Małgosia Bajka dla dzieci",
                "images": [{"url": "http://allegro.img/jas1.jpg"}],
                "description": {"sections": [{"items": [{"type": "TEXT", "content": "Bajka dla najmłodszych"}]}]},
                "parameters": [{"name": "EAN", "values": ["5901234567890"]}],
            },
            {
                "name": "Jaś i Małgosia wydanie kolekcjonerskie",
                "images": [{"url": "http://allegro.img/jas2.jpg"}],
                "description": "Kolekcjonerskie wydanie w twardej oprawie",
                "parameters": [{"name": "ISBN", "values": ["9788301000005"]}],
            },
            {
                "name": "Jaś i Małgosia puzzle i książeczka",
                "images": [{"url": "http://allegro.img/jas3.jpg"}],
                "parameters": [{"name": "Kod producenta", "values": ["PROD123"]}],
            },
        ]
    }

    with (
        patch("app.utils.allegro.get_allegro_token", return_value="mock_token"),
        patch("app.utils.allegro.requests.get") as mock_get,
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_allegro_products
        mock_get.return_value = mock_resp

        candidates = fetch_allegro_candidates("Jaś i Małgosia", max_results=10)

        assert len(candidates) == 3
        assert candidates[0]["title"] == "Jaś i Małgosia Bajka dla dzieci"
        assert candidates[0]["barcode"] == "5901234567890"
        assert candidates[0]["cover_url"] == "http://allegro.img/jas1.jpg"
        assert candidates[1]["title"] == "Jaś i Małgosia wydanie kolekcjonerskie"
        assert candidates[1]["barcode"] == "9788301000005"
        assert candidates[2]["title"] == "Jaś i Małgosia puzzle i książeczka"
        assert candidates[2]["barcode"] == "PROD123"


def test_book_lookup_strategy_candidates_aggregation():
    """Verify BookLookupStrategy aggregates candidates across providers and returns candidates list."""
    strategy = BookLookupStrategy()

    mock_gb = [
        {"Title": "Dune", "Authors": ["Frank Herbert"], "data_source": "google_books", "cover_url": "http://dune1.jpg"},
        {"Title": "Dune Messiah", "Authors": ["Frank Herbert"], "data_source": "google_books", "cover_url": "http://dune2.jpg"},
    ]
    mock_allegro = [
        {"title": "Dune Edycja Limitowana", "data_source": "allegro", "cover_url": "http://dune_allegro.jpg"},
        {"title": "Dune Komiks", "data_source": "allegro", "cover_url": "http://dune_comic.jpg"},
    ]

    with (
        patch("app.strategies.book.fetch_google_books_candidates", return_value=mock_gb),
        patch("app.strategies.book.fetch_allegro_candidates", return_value=mock_allegro),
    ):
        candidates = strategy.lookup_candidates("Dune", max_results=4)
        assert len(candidates) == 4
        assert candidates[0]["Title"] == "Dune"
        assert candidates[1]["Title"] == "Dune Messiah"
        assert candidates[2]["title"] == "Dune Edycja Limitowana"
        assert candidates[3]["title"] == "Dune Komiks"

        # Lookup by title query returns top result + candidates list
        meta, provider = strategy.lookup("Dune", query="Dune", max_results=4)
        assert meta is not None
        assert meta["Title"] == "Dune"
        assert "candidates" in meta
        assert len(meta["candidates"]) == 4
        assert provider == "google_books"


def test_api_lookup_title_returns_multi_candidates(client, normal_user_headers):
    """Assert scanner title lookup for ambiguous titles returns >= 3 candidates without truncation."""
    mock_gb_candidates = [
        {
            "Title": "Jaś i Małgosia - Baśń",
            "title": "Jaś i Małgosia - Baśń",
            "Authors": ["Wilhelm Grimm", "Jacob Grimm"],
            "cover_url": "http://img/1.jpg",
            "barcode": "9788301000010",
            "data_source": "google_books",
        },
        {
            "Title": "Jaś i Małgosia - Teatrzyk",
            "title": "Jaś i Małgosia - Teatrzyk",
            "Authors": ["Jan Brzechwa"],
            "cover_url": "http://img/2.jpg",
            "barcode": "9788301000020",
            "data_source": "google_books",
        },
        {
            "Title": "Jaś i Małgosia - Wydanie Ilustrowane",
            "title": "Jaś i Małgosia - Wydanie Ilustrowane",
            "Authors": ["Jan Marcin Szancer"],
            "cover_url": "http://img/3.jpg",
            "barcode": "9788301000030",
            "data_source": "google_books",
        },
    ]

    with patch("app.utils.isbn.fetch_google_books_candidates", return_value=mock_gb_candidates):
        response = client.get("/api/lookup/Jaś%20i%20Małgosia?format=book", headers=normal_user_headers)

        assert response.status_code == 200
        json_data = response.json
        assert json_data["success"] is True
        assert json_data["error"] is None

        data = json_data["data"]
        assert data is not None
        assert data["title"] == "Jaś i Małgosia - Baśń"
        assert "candidates" in data
        assert isinstance(data["candidates"], list)
        assert len(data["candidates"]) >= 3

        # Assert every candidate has normalized attributes
        for candidate in data["candidates"]:
            assert "title" in candidate
            assert candidate["title"] is not None
            assert "format" in candidate
            assert candidate["format"] == "book"
            assert "already_in_collection" in candidate
