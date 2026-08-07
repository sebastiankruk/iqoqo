"""Tests for app.utils.isbn – ISBN canonicalization and external metadata lookup.

All external HTTP calls are mocked so these tests run fully offline.
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
#

from unittest.mock import MagicMock, patch

import requests

from app.utils.isbn import _lookup_google_books, _lookup_open_library, canonicalize_isbn, fetch_google_books_candidates, fetch_isbn_metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_get(json_data: object, status_code: int = 200) -> MagicMock:
    """Return a mock session whose ``.get()`` succeeds with *json_data*."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    return mock_session


def _mock_session_raising(exc: Exception) -> MagicMock:
    """Return a mock session whose ``.get()`` raises *exc*."""
    mock_session = MagicMock()
    mock_session.get.side_effect = exc
    return mock_session


# ---------------------------------------------------------------------------
# canonicalize_isbn
# ---------------------------------------------------------------------------


class TestCanonicalizeIsbn:
    """Unit tests for :func:`app.utils.isbn.canonicalize_isbn`."""

    def test_valid_isbn13_plain(self):
        assert canonicalize_isbn("9780553380163") == "9780553380163"

    def test_valid_isbn13_with_hyphens(self):
        assert canonicalize_isbn("978-0-553-38016-3") == "9780553380163"

    def test_valid_isbn13_with_spaces(self):
        assert canonicalize_isbn("978 0 553 38016 3") == "9780553380163"

    def test_valid_isbn13_979_prefix(self):
        # 9791032309919 has a valid check digit (verified manually).
        assert canonicalize_isbn("9791032309919") == "9791032309919"

    def test_valid_isbn10_plain(self):
        # 0553380168 → ISBN-13 9780553380163
        assert canonicalize_isbn("0553380168") == "9780553380163"

    def test_valid_isbn10_with_hyphens(self):
        assert canonicalize_isbn("0-553-38016-8") == "9780553380163"

    def test_valid_isbn10_x_check_digit(self):
        # 000000006X: weighted sum = 2*6 + 1*10 = 22, 22 % 11 == 0 → valid.
        # Converts to ISBN-13 9780000000064.
        assert canonicalize_isbn("000000006X") == "9780000000064"

    def test_polish_isbn_that_was_failing_in_prod(self):
        # 9788380694163 was returning 404 due to the isbnlib bug.
        assert canonicalize_isbn("9788380694163") == "9788380694163"

    def test_invalid_isbn13_bad_check_digit(self):
        assert canonicalize_isbn("9780553380164") is None  # last digit off by one

    def test_invalid_isbn13_wrong_prefix(self):
        assert canonicalize_isbn("1234567890128") is None  # prefix 123, not 978/979

    def test_invalid_isbn10_bad_check_digit(self):
        assert canonicalize_isbn("0553380169") is None  # last digit off by one

    def test_too_short(self):
        assert canonicalize_isbn("12345") is None

    def test_too_long(self):
        assert canonicalize_isbn("97805533801631234") is None

    def test_empty_string(self):
        assert canonicalize_isbn("") is None

    def test_non_numeric_garbage(self):
        assert canonicalize_isbn("not-an-isbn") is None


# ---------------------------------------------------------------------------
# _lookup_google_books
# ---------------------------------------------------------------------------

_GOOGLE_BOOKS_HIT = {
    "totalItems": 1,
    "items": [
        {
            "volumeInfo": {
                "title": "The Hobbit",
                "authors": ["J.R.R. Tolkien"],
            }
        }
    ],
}


class TestLookupGoogleBooks:
    """Unit tests for :func:`app.utils.isbn._lookup_google_books`."""

    def test_success_returns_title_and_authors(self):
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(_GOOGLE_BOOKS_HIT)):
            result = _lookup_google_books("9780553380163")
        assert result is not None
        assert result["Title"] == "The Hobbit"
        assert result["Authors"] == ["J.R.R. Tolkien"]
        assert result["Source"] == "Google Books"

    def test_no_items_returns_none(self):
        data = {"totalItems": 0, "items": []}
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_google_books("9780553380163")
        assert result is None

    def test_empty_title_returns_none(self):
        data = {"totalItems": 1, "items": [{"volumeInfo": {"title": "   ", "authors": []}}]}
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_google_books("9780553380163")
        assert result is None

    def test_missing_volume_info_returns_none(self):
        data = {"totalItems": 1, "items": [{}]}
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_google_books("9780553380163")
        assert result is None

    def test_request_exception_returns_none(self):
        with patch(
            "app.utils.isbn._make_session",
            return_value=_mock_session_raising(requests.RequestException("timeout")),
        ):
            result = _lookup_google_books("9780553380163")
        assert result is None

    def test_authors_are_preserved(self):
        data = {
            "totalItems": 1,
            "items": [{"volumeInfo": {"title": "Book", "authors": ["Alice", "Bob"]}}],
        }
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_google_books("9780553380163")
        assert result is not None
        assert result["Authors"] == ["Alice", "Bob"]


# ---------------------------------------------------------------------------
# _lookup_open_library
# ---------------------------------------------------------------------------

_OPEN_LIBRARY_HIT = {
    "ISBN:9780553380163": {
        "title": "The Hobbit",
        "authors": [{"name": "J.R.R. Tolkien"}],
    }
}


class TestLookupOpenLibrary:
    """Unit tests for :func:`app.utils.isbn._lookup_open_library`."""

    def test_success_returns_title_and_authors(self):
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(_OPEN_LIBRARY_HIT)):
            result = _lookup_open_library("9780553380163")
        assert result is not None
        assert result["Title"] == "The Hobbit"
        assert result["Authors"] == ["J.R.R. Tolkien"]
        assert result["Source"] == "Open Library"

    def test_success_does_not_leak_lowercase_authors_or_subjects(self):
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(_OPEN_LIBRARY_HIT)):
            result = _lookup_open_library("9780553380163")
        assert result is not None
        assert "authors" not in result
        assert "subjects" not in result
        assert result["Authors"] == ["J.R.R. Tolkien"]

    def test_empty_response_returns_none(self):
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get({})):
            result = _lookup_open_library("9780553380163")
        assert result is None

    def test_empty_title_returns_none(self):
        data = {"ISBN:x": {"title": "", "authors": []}}
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_open_library("9780553380163")
        assert result is None

    def test_request_exception_returns_none(self):
        with patch(
            "app.utils.isbn._make_session",
            return_value=_mock_session_raising(requests.RequestException("connect timeout")),
        ):
            result = _lookup_open_library("9780553380163")
        assert result is None

    def test_authors_with_empty_names_are_excluded(self):
        data = {
            "ISBN:x": {
                "title": "Some Book",
                "authors": [
                    {"name": "Author One"},
                    {"name": ""},
                    {"url": "http://openlibrary.org/authors/OL123"},
                ],
            }
        }
        with patch("app.utils.isbn._make_session", return_value=_mock_session_get(data)):
            result = _lookup_open_library("9780553380163")
        assert result is not None
        assert result["Authors"] == ["Author One"]


# ---------------------------------------------------------------------------
# fetch_isbn_metadata
# ---------------------------------------------------------------------------


class TestFetchIsbnMetadata:
    """Integration-style tests for :func:`app.utils.isbn.fetch_isbn_metadata`."""

    def test_google_books_hit_is_returned_directly(self):
        expected = {"Title": "The Hobbit", "Authors": ["J.R.R. Tolkien"]}
        with (
            patch("app.utils.isbn._lookup_google_books", return_value=expected) as mock_gb,
            patch("app.utils.isbn._lookup_open_library") as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163")

        assert result == expected
        mock_gb.assert_called_once_with("9780553380163")
        mock_ol.assert_not_called()

    def test_falls_back_to_open_library_when_google_books_returns_none(self):
        expected = {"Title": "The Hobbit", "Authors": ["J.R.R. Tolkien"]}
        with (
            patch("app.utils.isbn._lookup_google_books", return_value=None),
            patch("app.utils.isbn._lookup_open_library", return_value=expected) as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163")

        assert result == expected
        mock_ol.assert_called_once_with("9780553380163")

    def test_returns_none_when_both_sources_fail(self):
        with (
            patch("app.utils.isbn._lookup_google_books", return_value=None),
            patch("app.utils.isbn._lookup_open_library", return_value=None),
        ):
            result = fetch_isbn_metadata("9780553380163")

        assert result is None
