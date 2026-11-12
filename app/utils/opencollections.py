"""SSRF-safe OpenCollections.org metadata lookup client.

Provides resolution of OpenCollections.org cultural/media records and search
candidates using ``app.utils.http_client.safe_get`` with a 5.0s timeout floor,
strict Pydantic validation, outbound telemetry, and field-level ``_provenance``.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import logging
import re
import time
import urllib.parse
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.telemetry import record_outbound_telemetry
from app.utils.http_client import SSRFError, safe_get

logger = logging.getLogger(__name__)

OPENCOLLECTIONS_BASE_URL = "https://opencollections.org/api/v1"
_TIMEOUT = (3.0, 5.0)  # (connect, read) — 5.0s read timeout floor
_VALID_RECORD_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class _OpenCollectionsRecordSchema(BaseModel):
    """Strict validation schema for an OpenCollections.org API record."""

    model_config = ConfigDict(extra="allow")

    id: str | int | None = None
    uri: str | None = None
    title: str = Field(..., min_length=1, max_length=1000)
    creators: list[str] | str | None = None
    authors: list[str] | str | None = None
    publication_date: str | int | None = None
    year: str | int | None = None
    publisher: str | None = None
    description: str | None = None
    format: str | None = None
    media_type: str | None = None
    isbn: str | None = None
    ean: str | None = None
    upc: str | None = None
    cover_url: str | None = None
    categories: list[str] | None = None


def _normalize_authors(raw_authors: list[str] | str | None) -> list[str]:
    """Normalize author/creator values into a non-empty list of strings."""
    if isinstance(raw_authors, list):
        return [str(a).strip() for a in raw_authors if str(a).strip()]
    if isinstance(raw_authors, str) and raw_authors.strip():
        return [raw_authors.strip()]
    return []


def _normalize_opencollections_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a raw OpenCollections.org JSON payload into iqoqo FRBR metadata."""
    try:
        parsed = _OpenCollectionsRecordSchema(**raw)
    except ValidationError as exc:
        logger.warning("OpenCollections payload failed validation: %s", exc)
        return None

    record_uri = parsed.uri
    if not record_uri and parsed.id is not None:
        safe_id = urllib.parse.quote(str(parsed.id), safe="")
        record_uri = f"https://opencollections.org/records/{safe_id}"

    authors = _normalize_authors(parsed.creators) or _normalize_authors(parsed.authors)
    published_date = str(parsed.publication_date or parsed.year) if (parsed.publication_date or parsed.year) is not None else None
    isbn = parsed.isbn or parsed.ean or parsed.upc

    meta: dict[str, Any] = {
        "Title": parsed.title.strip(),
        "Authors": authors,
        "Format": (parsed.format or parsed.media_type or "book").strip(),
    }
    provenance: dict[str, str] = {"Title": "opencollections", "Format": "opencollections"}

    if authors:
        provenance["Authors"] = "opencollections"
    if published_date:
        meta["PublishedDate"] = published_date
        provenance["PublishedDate"] = "opencollections"
    if parsed.publisher:
        meta["Publisher"] = parsed.publisher.strip()
        provenance["Publisher"] = "opencollections"
    if parsed.description:
        meta["Description"] = parsed.description.strip()
        provenance["Description"] = "opencollections"
    if isbn:
        meta["ISBN"] = str(isbn).strip()
        provenance["ISBN"] = "opencollections"
    if parsed.categories:
        meta["Categories"] = [str(c).strip() for c in parsed.categories if str(c).strip()]
        provenance["Categories"] = "opencollections"
    if parsed.cover_url and parsed.cover_url.startswith("https://"):
        meta["CoverUrl"] = parsed.cover_url
        provenance["CoverUrl"] = "opencollections"
    if record_uri and record_uri.startswith(("https://", "http://")):
        meta["lod_links"] = {"opencollections_uri": record_uri}
        provenance["lod_links"] = "opencollections"

    meta["_provenance"] = provenance
    return meta


def fetch_opencollections_record(identifier: str) -> dict[str, Any] | None:
    """Fetch and normalize a single OpenCollections.org record by identifier or barcode.

    Args:
        identifier: Record ID, ISBN, or barcode.

    Returns:
        Normalized metadata dictionary with ``_provenance`` and ``lod_links``, or ``None``.
    """
    cleaned = identifier.strip()
    if not cleaned or not _VALID_RECORD_ID_RE.match(cleaned):
        return None

    encoded_id = urllib.parse.quote(cleaned, safe="")
    url = f"{OPENCOLLECTIONS_BASE_URL}/records/{encoded_id}"
    start = time.monotonic()
    status_code: int | None = None
    error_type: str | None = None

    try:
        resp = safe_get(url, timeout=_TIMEOUT, headers={"Accept": "application/json"})
        status_code = resp.status_code
        if resp.status_code != 200:
            error_type = f"http_{resp.status_code}"
            return None
        payload = resp.json()
        if not isinstance(payload, dict):
            error_type = "invalid_json_shape"
            return None
        return _normalize_opencollections_record(payload)
    except SSRFError as exc:
        error_type = "ssrf_blocked"
        logger.warning("SSRF blocked OpenCollections lookup for %r: %s", cleaned, exc)
        return None
    except requests.RequestException as exc:
        error_type = type(exc).__name__
        logger.warning("OpenCollections request failed for %r: %s", cleaned, exc)
        return None
    except ValueError as exc:
        error_type = "json_decode_error"
        logger.warning("OpenCollections JSON decode error for %r: %s", cleaned, exc)
        return None
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000.0
        record_outbound_telemetry(
            provider="opencollections",
            operation="record_lookup",
            duration_ms=elapsed_ms,
            status_code=status_code,
            error_type=error_type,
        )


def search_opencollections_candidates(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search OpenCollections.org for candidate bibliographic/cultural records.

    Args:
        query: Search query string.
        max_results: Maximum number of normalized candidates to return (1-25).

    Returns:
        List of normalized metadata dictionaries.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    limit = max(1, min(int(max_results), 25))
    encoded_q = urllib.parse.quote_plus(cleaned)
    url = f"{OPENCOLLECTIONS_BASE_URL}/search?q={encoded_q}&limit={limit}"
    start = time.monotonic()
    status_code: int | None = None
    error_type: str | None = None

    try:
        resp = safe_get(url, timeout=_TIMEOUT, headers={"Accept": "application/json"})
        status_code = resp.status_code
        if resp.status_code != 200:
            error_type = f"http_{resp.status_code}"
            return []
        payload = resp.json()
        raw_items = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(raw_items, list):
            return []
        results: list[dict[str, Any]] = []
        for entry in raw_items[:limit]:
            if isinstance(entry, dict):
                normalized = _normalize_opencollections_record(entry)
                if normalized is not None:
                    results.append(normalized)
        return results
    except SSRFError as exc:
        error_type = "ssrf_blocked"
        logger.warning("SSRF blocked OpenCollections search for %r: %s", cleaned, exc)
        return []
    except requests.RequestException as exc:
        error_type = type(exc).__name__
        logger.warning("OpenCollections search failed for %r: %s", cleaned, exc)
        return []
    except ValueError as exc:
        error_type = "json_decode_error"
        logger.warning("OpenCollections search JSON decode error for %r: %s", cleaned, exc)
        return []
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000.0
        record_outbound_telemetry(
            provider="opencollections",
            operation="search",
            duration_ms=elapsed_ms,
            status_code=status_code,
            error_type=error_type,
        )
