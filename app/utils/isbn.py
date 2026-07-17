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
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

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
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    if api_key:
        url += f"&key={api_key}"

    try:
        session = _make_session()
        response = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Google Books request failed for %s: %s", isbn, exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
            raise
        return None

    if not data.get("totalItems") or not data.get("items"):
        logger.debug("Google Books: no results for %s", isbn)
        return None

    info = data["items"][0].get("volumeInfo", {})
    title = info.get("title", "").strip()
    if not title:
        return None

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
    return metadata


def _lookup_open_library(isbn: str) -> dict[str, Any] | None:
    """Fetch metadata from the Open Library Books API.

    Args:
        isbn: A canonical 13-digit ISBN string.

    Returns:
        ``{"Title": str, "Authors": list[str]}`` on success, ``None``
        if the API returns no results or the request fails.
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        session = _make_session()
        response = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Open Library request failed for %s: %s", isbn, exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
            raise
        return None

    if not data:
        logger.debug("Open Library: no results for %s", isbn)
        return None

    book = next(iter(data.values()))
    title = book.get("title", "").strip()
    if not title:
        return None

    authors = [a.get("name", "") for a in book.get("authors", []) if a.get("name")]

    # Open Library sometimes stores description in 'notes'
    description = book.get("notes", "")
    if isinstance(description, dict):
        description = description.get("value", "")

    categories = [s.get("name", "") for s in book.get("subjects", []) if s.get("name")]

    # Clone raw data and add standard keys.
    # The raw OL response contains ``authors`` and ``subjects`` as lists of
    # *dicts* (e.g. ``[{"name": "…", "url": "…"}]``).  These must NOT leak
    # downstream — we delete the raw keys and replace them with the canonical
    # capitalized ``Authors`` and ``Categories`` which hold plain strings.
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
    return metadata


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_isbn_metadata(isbn: str) -> dict[str, Any] | None:
    """Look up book metadata for *isbn* from external sources.

    Tries Google Books first; falls back to Open Library if Google Books
    returns no results.  Both sources are queried with the shared retry
    policy and generous timeouts (see module constants).

    Args:
        isbn: A canonical 13-digit ISBN string.  Use
              :func:`canonicalize_isbn` to obtain one from raw user input
              before calling this function.

    Returns:
        A dict containing standard keys (Title, Authors, Description, Categories)
        plus the full raw metadata payload from the provider.
    """
    metadata = _lookup_google_books(isbn)
    if metadata:
        logger.info("ISBN %s resolved via Google Books", isbn)
        return metadata

    logger.debug("Falling back to Open Library for ISBN %s", isbn)

    metadata = _lookup_open_library(isbn)
    if metadata:
        logger.info("ISBN %s resolved via Open Library", isbn)
        return metadata

    logger.warning("No metadata found for ISBN %s from any upstream source", isbn)
    return None
