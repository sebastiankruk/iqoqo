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

from app.utils.isbn import (
    ISBNProviderOutcome,
    ISBNProviderOutcomeStatus,
    _lookup_google_books,
    _lookup_google_books_outcome,
    _lookup_open_library,
    _lookup_open_library_outcome,
    canonicalize_isbn,
    fetch_google_books_candidates,
    fetch_isbn_metadata,
)

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
        gb_success = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata=expected,
            provider="google_books",
        )
        with (
            patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_success) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome") as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163")

        assert result == expected
        mock_gb.assert_called_once_with("9780553380163")
        mock_ol.assert_not_called()

    def test_falls_back_to_open_library_when_google_books_returns_none(self):
        expected = {"Title": "The Hobbit", "Authors": ["J.R.R. Tolkien"]}
        gb_no_result = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="google_books",
        )
        ol_success = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata=expected,
            provider="open_library",
        )
        with (
            patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_no_result) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_success) as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163")

        assert result == expected
        mock_gb.assert_called_once_with("9780553380163")
        mock_ol.assert_called_once_with("9780553380163")

    def test_returns_none_when_both_sources_fail(self):
        with (
            patch("app.utils.isbn._lookup_google_books_outcome") as mock_gb_outcome,
            patch("app.utils.isbn._lookup_open_library_outcome") as mock_ol_outcome,
        ):
            mock_gb_outcome.return_value = MagicMock(status="no_result", metadata=None)
            mock_ol_outcome.return_value = MagicMock(status="no_result", metadata=None)
            result = fetch_isbn_metadata("9780553380163")

        assert result is None

    def test_google_transient_failure_falls_back_to_open_library(self):
        """Task 3.1: Google 429/503 fallback to Open Library (The Rough Guide to the USA)."""
        ol_meta = {
            "Title": "The Rough Guide to the USA",
            "Authors": ["Samantha Cook"],
            "Source": "Open Library",
        }
        gb_transient = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
            provider="google_books",
            error_detail="HTTP 503",
        )
        ol_success = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata=ol_meta,
            provider="open_library",
        )

        with (
            patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_transient) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_success) as mock_ol,
        ):
            result = fetch_isbn_metadata("9781843537861", retry_delay=0)

        assert result == ol_meta
        assert result["Title"] == "The Rough Guide to the USA"
        assert result["Source"] == "Open Library"
        mock_gb.assert_called_once_with("9781843537861")
        mock_ol.assert_called_once_with("9781843537861")

    def test_google_definitive_no_result_does_not_retry_google(self):
        """Task 3.2: Google returns successful empty result; verify Google is NOT retried."""
        gb_no_result = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="google_books",
        )
        ol_no_result = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
        )

        with (
            patch("app.utils.isbn._lookup_google_books_outcome", return_value=gb_no_result) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_no_result) as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163", retry_delay=0)

        assert result is None
        # Google should be queried exactly once (no retry on definitive no_result)
        assert mock_gb.call_count == 1
        mock_ol.assert_called_once_with("9780553380163")

    def test_google_transient_open_library_empty_google_retry_succeeds(self):
        """Task 3.3: Google fails transiently, OL has no result, single Google retry succeeds."""
        gb_transient = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
            provider="google_books",
            error_detail="HTTP 429",
        )
        ol_no_result = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
        )
        gb_success = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.SUCCESS,
            metadata={"Title": "Retry Success Book", "Authors": ["Jane Doe"], "Source": "Google Books"},
            provider="google_books",
        )

        with (
            patch("app.utils.isbn._lookup_google_books_outcome", side_effect=[gb_transient, gb_success]) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_no_result) as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163", retry_delay=0)

        assert result is not None
        assert result["Title"] == "Retry Success Book"
        assert mock_gb.call_count == 2
        mock_ol.assert_called_once_with("9780553380163")

    def test_both_google_attempts_fail_and_chain_continues(self):
        """Task 3.4: Both Google attempts fail transiently, returns None so strategy continues downstream."""
        gb_transient = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
            provider="google_books",
            error_detail="HTTP 500",
        )
        ol_no_result = ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
        )

        with (
            patch("app.utils.isbn._lookup_google_books_outcome", side_effect=[gb_transient, gb_transient]) as mock_gb,
            patch("app.utils.isbn._lookup_open_library_outcome", return_value=ol_no_result) as mock_ol,
        ):
            result = fetch_isbn_metadata("9780553380163", retry_delay=0)

        assert result is None
        assert mock_gb.call_count == 2
        mock_ol.assert_called_once_with("9780553380163")

        # Verify BookLookupStrategy moves to Allegro when fetch_isbn_metadata returns None
        from app.strategies.book import BookLookupStrategy

        strategy = BookLookupStrategy()
        with (
            patch("app.strategies.book.fetch_isbn_metadata", return_value=None),
            patch("app.strategies.book.fetch_allegro_metadata") as mock_allegro,
        ):
            mock_allegro.return_value = {"Title": "Allegro Book", "Source": "Allegro"}
            meta, provider = strategy.lookup("9780553380163")

        assert meta is not None
        assert provider == "allegro"
        assert meta["data_source"] == "allegro"


def test_google_books_outcome_scrubs_api_key_in_logs():
    """Verify that Google Books HTTP/request error handling redacts API keys."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests", response=mock_response)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response

    with (
        patch.dict("os.environ", {"GOOGLE_BOOKS_API_KEY": "SECRET_KEY_12345"}),
        patch("app.utils.isbn._make_session", return_value=mock_session),
    ):
        outcome = _lookup_google_books_outcome("9780553380163")

    assert outcome.status == ISBNProviderOutcomeStatus.TRANSIENT_FAILURE
    assert outcome.error_detail == "HTTP 429"


@patch("app.utils.isbn._make_session")
def test_fetch_google_books_candidates_url_encoding(mock_session):
    mock_get = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response
    mock_session.return_value.get = mock_get

    fetch_google_books_candidates("Jaś i Małgosia", max_results=5)

    # Verify that requests.get was called with correct params dictionary
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.googleapis.com/books/v1/volumes"
    assert "params" in kwargs
    assert kwargs["params"]["q"] == "Jaś i Małgosia"
    assert kwargs["params"]["maxResults"] == 5
