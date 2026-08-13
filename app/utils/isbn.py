"""ISBN metadata lookup utilities.

Provides ISBN canonicalization and metadata retrieval from two upstream
services, tried in order:

1. **Google Books API** – fast, high availability, good English coverage.
2. **Open Library Books API** – broader language coverage, open data.

Both services are queried with a shared retry policy (3 attempts, 1.5×
exponential back-off) and generous connection / read timeouts so that
slow cold-start DNS or TLS negotiation does not immediately return a 404
to the caller.

Typical usage::

    from app.utils.isbn import canonicalize_isbn, fetch_isbn_metadata

    isbn = canonicalize_isbn(raw_input)
    if isbn is None:
        return error("Invalid ISBN")
    meta = fetch_isbn_metadata(isbn)
    if meta is None:
        return error("Book not found")
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

import logging
import os
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider outcome representation
# ---------------------------------------------------------------------------


class ISBNProviderOutcomeStatus(StrEnum):
    """Status classification for an external ISBN provider attempt."""

    SUCCESS = "success"
    NO_RESULT = "no_result"
    TRANSIENT_FAILURE = "transient_failure"


@dataclass
class ISBNProviderOutcome:
    """Internal outcome model for external ISBN metadata queries."""

    status: ISBNProviderOutcomeStatus
    metadata: dict[str, Any] | None = None
    provider: str = ""
    error_detail: str | None = None


# ---------------------------------------------------------------------------
# HTTP session configuration
# ---------------------------------------------------------------------------

# (connect timeout, read timeout) in seconds.
# Connect: time to establish TCP + TLS with the upstream host.
# Read: time to receive the full response body after the connection is open.
_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7

# Retry policy: 3 attempts on transient errors.
# Delays after failures: ~0.5 s, ~1 s, ~2 s.
_RETRY_POLICY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False,
)


def _make_session() -> requests.Session:
    """Return a :class:`requests.Session` with the shared retry adapter mounted.

    A new session is created per call so that the retry state is never shared
    across different ISBN lookups happening in parallel request threads.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "iqoqo-catalog-app/1.0 (contact@iqoqo.cc)"})
    adapter = HTTPAdapter(max_retries=_RETRY_POLICY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# ISBN canonicalization
# ---------------------------------------------------------------------------


def canonicalize_isbn(raw: str) -> str | None:
    """Return a canonical 13-digit ISBN string, or ``None`` if invalid.

    Accepts ISBN-10 and ISBN-13 in any common notation (hyphens, spaces,
    mixed case).  ISBN-10 inputs are converted to ISBN-13 (978-prefix).

    Args:
        raw: Raw user input, e.g. ``"978-0-553-38016-8"`` or ``"0553380168"``.

    Returns:
        A 13-digit string (e.g. ``"9780553380163"``), or ``None`` if the
        input cannot be parsed as a valid ISBN.
    """
    # Strip everything except digits and trailing X (ISBN-10 check character).
    stripped = re.sub(r"[^0-9Xx]", "", raw).upper()

    if len(stripped) == 10:
        # Validate ISBN-10 check digit (modulo 11).
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(stripped))
        if total % 11 != 0:
            return None
        # Convert to ISBN-13: prepend "978" and recalculate check digit.
        body = "978" + stripped[:9]
        check = (10 - sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(body)) % 10) % 10
        return body + str(check)

    if len(stripped) == 13:
        # Only 978/979 prefixes are defined by the ISBN-13 standard.
        if stripped[:3] not in ("978", "979"):
            return None
        # Validate ISBN-13 check digit.
        check = (10 - sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(stripped[:12])) % 10) % 10
        if int(stripped[12]) != check:
            return None
        return stripped

    return None


# ---------------------------------------------------------------------------
# Upstream service adapters
# ---------------------------------------------------------------------------


def _lookup_google_books_outcome(isbn: str) -> ISBNProviderOutcome:
    """Fetch metadata outcome from the Google Books API without leaking secrets.

    Args:
        isbn: A canonical 13-digit ISBN string.

    Returns:
        :class:`ISBNProviderOutcome` indicating success, definitive no-result,
        or transient failure.
    """
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    if api_key:
        url += f"&key={api_key}"

    try:
        session = _make_session()
        response = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        safe_msg = f"HTTP {status_code}" if status_code else "HTTPError"
        logger.warning("Google Books request returned HTTP status %s for ISBN %s", safe_msg, isbn)
        if status_code in (429, 500, 502, 503, 504) or (status_code and status_code >= 500):
            return ISBNProviderOutcome(
                status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
                provider="google_books",
                error_detail=safe_msg,
            )
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="google_books",
            error_detail=safe_msg,
        )
    except (requests.RequestException, ValueError) as exc:
        safe_exc = re.sub(r"key=[^&]+", "key=[REDACTED]", str(exc))
        logger.warning("Google Books request failed for ISBN %s: %s", isbn, safe_exc)
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
            provider="google_books",
            error_detail=safe_exc,
        )

    if not data.get("totalItems") or not data.get("items"):
        logger.debug("Google Books: no results for %s", isbn)
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="google_books",
        )

    info = data["items"][0].get("volumeInfo", {})
    title = info.get("title", "").strip()
    if not title:
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="google_books",
        )

    # Normalize optional fields to guard against null / unexpected types.
    raw_description = info.get("description")
    description = raw_description.strip() if isinstance(raw_description, str) else ""

    def __normalize_list_field(field):
        raw_value = info.get(field)
        if isinstance(raw_value, list):
            return [str(v).strip() for v in raw_value if v and str(v).strip()]
        if isinstance(raw_value, str):
            return [str(v).strip() for v in raw_value.strip().split(",") if v and str(v).strip()] if raw_value.strip() else []
        return []

    authors = __normalize_list_field("authors")
    categories = __normalize_list_field("categories")

    # Clone the raw data so we don't mutate the original, then add standard keys
    metadata = dict(info)
    metadata.update(
        {
            "Title": title,
            "Authors": authors,
            "Description": description,
            "Categories": categories,
            "Source": "Google Books",
        }
    )
    return ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata=metadata,
        provider="google_books",
    )


def _lookup_google_books(isbn: str) -> dict[str, Any] | None:
    """Fetch metadata from the Google Books API.

    Uses the public (unauthenticated) ``volumes`` endpoint which does not
    require an API key for low-volume lookups.

    Args:
        isbn: A canonical 13-digit ISBN string.

    Returns:
        ``{"Title": str, "Authors": list[str]}`` on success, ``None``
        if the API returns no results or the request fails.
    """
    outcome = _lookup_google_books_outcome(isbn)
    return outcome.metadata if outcome.status == ISBNProviderOutcomeStatus.SUCCESS else None


def fetch_google_books_candidates(query: str, max_results: int = 5) -> list[dict]:
    """Search Google Books by text query and return candidates.

    Args:
        query: Free-text search term (e.g. title).
        max_results: Maximum number of results to return.

    Returns:
        List of normalised metadata dicts, possibly empty.
    """
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    url = "https://www.googleapis.com/books/v1/volumes"
    params: dict[str, Any] = {"q": query, "maxResults": max_results}
    if api_key:
        params["key"] = api_key

    try:
        session = _make_session()
        response = session.get(url, params=params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        safe_exc = re.sub(r"key=[^&]+", "key=[REDACTED]", str(exc))
        logger.debug("Google Books request failed for %s: %s", query, safe_exc)
        return []

    if not data.get("totalItems") or not data.get("items"):
        return []

    def __normalize_list_field(info: dict, field: str):
        raw_value = info.get(field)
        if isinstance(raw_value, list):
            return [str(v).strip() for v in raw_value if v and str(v).strip()]
        if isinstance(raw_value, str):
            return [str(v).strip() for v in raw_value.strip().split(",") if v and str(v).strip()] if raw_value.strip() else []
        return []

    results = []
    for item in data["items"]:
        info = item.get("volumeInfo", {})
        title = info.get("title", "").strip()
        if not title:
            continue

        raw_description = info.get("description")
        description = raw_description.strip() if isinstance(raw_description, str) else ""

        # Get ISBN if present
        isbn = None
        for identifier in info.get("industryIdentifiers", []):
            if identifier.get("type") in ("ISBN_13", "ISBN_10"):
                isbn = canonicalize_isbn(identifier.get("identifier", ""))
                if isbn:
                    break

        metadata = dict(info)
        metadata.update(
            {
                "Title": title,
                "Authors": __normalize_list_field(info, "authors"),
                "Description": description,
                "Categories": __normalize_list_field(info, "categories"),
                "Source": "Google Books",
                "barcode": isbn,
                "data_source": "google_books",
            }
        )

        # Add cover url mapping for frontend consistency
        if "imageLinks" in info and isinstance(info["imageLinks"], dict):
            metadata["cover_url"] = info["imageLinks"].get("thumbnail") or info["imageLinks"].get("smallThumbnail")

        results.append(metadata)

    return results


def _lookup_open_library_outcome(isbn: str) -> ISBNProviderOutcome:
    """Fetch metadata outcome from the Open Library Books API.

    Args:
        isbn: A canonical 13-digit ISBN string.

    Returns:
        :class:`ISBNProviderOutcome` indicating success, definitive no-result,
        or transient failure.
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        session = _make_session()
        response = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        safe_msg = f"HTTP {status_code}" if status_code else "HTTPError"
        logger.warning("Open Library request returned HTTP status %s for ISBN %s", safe_msg, isbn)
        if status_code in (429, 500, 502, 503, 504) or (status_code and status_code >= 500):
            return ISBNProviderOutcome(
                status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
                provider="open_library",
                error_detail=safe_msg,
            )
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
            error_detail=safe_msg,
        )
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Open Library request failed for ISBN %s: %s", isbn, exc)
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.TRANSIENT_FAILURE,
            provider="open_library",
            error_detail=str(exc),
        )

    if not data:
        logger.debug("Open Library: no results for %s", isbn)
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
        )

    book = next(iter(data.values()))
    title = book.get("title", "").strip()
    if not title:
        return ISBNProviderOutcome(
            status=ISBNProviderOutcomeStatus.NO_RESULT,
            provider="open_library",
        )

    authors = [a.get("name", "") for a in book.get("authors", []) if a.get("name")]

    # Open Library sometimes stores description in 'notes'
    description = book.get("notes", "")
    if isinstance(description, dict):
        description = description.get("value", "")

    categories = [s.get("name", "") for s in book.get("subjects", []) if s.get("name")]

    # Clone raw data and add standard keys.
    metadata = dict(book)
    metadata.pop("authors", None)
    metadata.pop("subjects", None)
    metadata.update(
        {
            "Title": title,
            "Authors": authors,
            "Description": description,
            "Categories": categories,
            "Source": "Open Library",
        }
    )
    return ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata=metadata,
        provider="open_library",
    )


def _lookup_open_library(isbn: str) -> dict[str, Any] | None:
    """Fetch metadata from the Open Library Books API.

    Args:
        isbn: A canonical 13-digit ISBN string.

    Returns:
        ``{"Title": str, "Authors": list[str]}`` on success, ``None``
        if the API returns no results or the request fails.
    """
    outcome = _lookup_open_library_outcome(isbn)
    return outcome.metadata if outcome.status == ISBNProviderOutcomeStatus.SUCCESS else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_isbn_metadata(isbn: str, retry_delay: float = 1.0) -> dict[str, Any] | None:
    """Look up book metadata for *isbn* from external sources.

    Tries Google Books first. If Google Books fails transiently (e.g. 429/5xx),
    immediately attempts Open Library. If Open Library has no metadata, retries
    Google Books once after a short delay (*retry_delay*).

    Args:
        isbn: A canonical 13-digit ISBN string. Use :func:`canonicalize_isbn` to
              obtain one from raw user input before calling this function.
        retry_delay: Delay in seconds before a single Google Books retry when
                     Google Books initially failed transiently and Open Library
                     had no result. Defaults to 1.0.

    Returns:
        A dict containing standard keys (Title, Authors, Description, Categories)
        plus the full raw metadata payload from the provider, or ``None``.
    """
    google_outcome = _lookup_google_books_outcome(isbn)
    if google_outcome.status == ISBNProviderOutcomeStatus.SUCCESS:
        logger.info("ISBN %s resolved via Google Books", isbn)
        return google_outcome.metadata

    if google_outcome.status == ISBNProviderOutcomeStatus.NO_RESULT:
        logger.debug("Google Books returned no results for ISBN %s, checking Open Library", isbn)
        ol_outcome = _lookup_open_library_outcome(isbn)
        if ol_outcome.status == ISBNProviderOutcomeStatus.SUCCESS:
            logger.info("ISBN %s resolved via Open Library", isbn)
            return ol_outcome.metadata
        logger.warning("No metadata found for ISBN %s from Google Books or Open Library", isbn)
        return None

    # Google Books returned transient_failure
    logger.warning("Google Books transient failure for ISBN %s; attempting Open Library immediately", isbn)
    ol_outcome = _lookup_open_library_outcome(isbn)
    if ol_outcome.status == ISBNProviderOutcomeStatus.SUCCESS:
        logger.info("ISBN %s resolved via Open Library after Google Books transient failure", isbn)
        return ol_outcome.metadata

    # Open Library has no result (or also failed transiently), and Google Books failed transiently on first attempt
    logger.warning(
        "Open Library had no metadata for ISBN %s after Google Books transient failure; retrying Google Books once",
        isbn,
    )
    if retry_delay > 0:
        time.sleep(retry_delay)

    retry_google_outcome = _lookup_google_books_outcome(isbn)
    if retry_google_outcome.status == ISBNProviderOutcomeStatus.SUCCESS:
        logger.info("ISBN %s resolved via Google Books retry", isbn)
        return retry_google_outcome.metadata

    logger.warning("No metadata found for ISBN %s from any upstream source after retry", isbn)
    return None
