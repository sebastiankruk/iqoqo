"""Rebrickable v3 API metadata lookup utilities for LEGO sets.

Provides SSRF-safe resolution of LEGO set metadata by set number and text search,
using Fernet-encrypted credentials from InstanceSettings and recording field-level provenance.
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

from app.core.telemetry import record_outbound_telemetry
from app.utils.http_client import SSRFError, safe_get

logger = logging.getLogger(__name__)

_REBRICKABLE_BASE_URL = "https://rebrickable.com/api/v3/lego"
_TIMEOUT = (3, 7)  # (connect, read)

# In-memory cache for theme ID to name mappings
_THEME_CACHE: dict[int, str] = {}


def normalize_set_number(raw: str) -> str:
    """Normalize a LEGO set number to Rebrickable canonical format (e.g. '10318' -> '10318-1').

    Args:
        raw: Raw set number string (e.g., '10318', '10318-1', '75192').

    Returns:
        Canonical set number with hyphenated version suffix.
    """
    cleaned = raw.strip()
    if re.match(r"^\d{4,6}$", cleaned):
        return f"{cleaned}-1"
    return cleaned


def is_set_number_format(query: str) -> bool:
    """Check if a query string matches LEGO set number syntax (e.g. '10318' or '10318-1')."""
    return bool(re.match(r"^\d{4,6}(-\d+)?$", query.strip()))


def get_rebrickable_api_key() -> str | None:
    """Retrieve Rebrickable API key from ConfigService (DB settings) or environment."""
    try:
        from app.core.config_service import ConfigService

        val = ConfigService.get("REBRICKABLE_API_KEY")
        if val:
            return str(val).strip()
    except Exception:
        pass

    try:
        from flask import current_app

        if current_app and current_app.config.get("REBRICKABLE_API_KEY"):
            return str(current_app.config["REBRICKABLE_API_KEY"]).strip()
    except RuntimeError:
        pass

    env_val = os.environ.get("REBRICKABLE_API_KEY")
    return env_val.strip() if env_val else None


def _fetch_theme_name(theme_id: int, headers: dict[str, str]) -> str | None:
    """Resolve theme name from Rebrickable theme API with in-memory caching."""
    if theme_id in _THEME_CACHE:
        return _THEME_CACHE[theme_id]

    url = f"{_REBRICKABLE_BASE_URL}/themes/{theme_id}/"
    try:
        record_outbound_telemetry("rebrickable", headers, url=url)
        response = safe_get(url, headers=headers, timeout=_TIMEOUT)
        if response.status_code == 200:
            name = response.json().get("name")
            if name:
                _THEME_CACHE[theme_id] = name
                return name
    except (requests.RequestException, SSRFError, ValueError) as exc:
        logger.debug("Failed to resolve Rebrickable theme %s: %s", theme_id, exc)
    return None


def _fetch_minifig_count(set_num: str, headers: dict[str, str]) -> int:
    """Fetch count of minifigures included with a set."""
    url = f"{_REBRICKABLE_BASE_URL}/sets/{set_num}/minifigs/"
    try:
        record_outbound_telemetry("rebrickable", headers, url=url)
        response = safe_get(url, headers=headers, timeout=_TIMEOUT)
        if response.status_code == 200:
            count = response.json().get("count")
            if isinstance(count, int):
                return count
    except (requests.RequestException, SSRFError, ValueError) as exc:
        logger.debug("Failed to resolve Rebrickable minifigs for set %s: %s", set_num, exc)
    return 0


def _infer_lego_format(title: str, theme: str | None) -> str:
    """Infer canonical physical sub-format for a LEGO set based on title and theme."""
    title_lower = title.lower()
    theme_lower = (theme or "").lower()

    if "ucs" in title_lower or "ultimate collector" in title_lower:
        return "ucs_collector_set"
    if "technic" in title_lower or theme_lower == "technic":
        return "technic_set"
    if "modular" in title_lower or "modular building" in theme_lower:
        return "modular_building"
    if "minifigure" in title_lower or "cmf" in title_lower or "series" in theme_lower:
        return "minifigure_series"
    if "polybag" in title_lower or "promo" in title_lower:
        return "polybag"
    return "standard_set"


def _format_rebrickable_set_payload(
    set_data: dict[str, Any],
    headers: dict[str, str],
    barcode: str | None = None,
) -> dict[str, Any]:
    """Format raw Rebrickable set API dictionary into canonical iqoqo metadata dictionary."""
    set_num = set_data.get("set_num", "")
    title = set_data.get("name") or "Unknown LEGO Set"
    year = set_data.get("year")
    piece_count = set_data.get("num_parts")
    cover_url = set_data.get("set_img_url")
    external_url = set_data.get("set_url")
    theme_id = set_data.get("theme_id")

    theme_name = _fetch_theme_name(theme_id, headers) if isinstance(theme_id, int) else None
    minifig_count = _fetch_minifig_count(set_num, headers) if set_num else 0
    format_val = _infer_lego_format(title, theme_name)

    meta: dict[str, Any] = {
        "title": title,
        "set_number": set_num,
        "set_num": set_num,
        "year": year,
        "piece_count": piece_count,
        "num_parts": piece_count,
        "minifig_count": minifig_count,
        "num_minifigs": minifig_count,
        "format": format_val,
        "category": "lego",
        "data_source": "rebrickable",
    }

    if theme_name:
        meta["theme"] = theme_name
        meta["genres"] = [theme_name]
    if cover_url:
        meta["cover_url"] = cover_url
    if external_url:
        meta["external_url"] = external_url
    if barcode:
        meta["barcode"] = barcode

    # Record field-level provenance
    meta["_provenance"] = {k: "rebrickable" for k, v in meta.items() if k != "_provenance" and v not in (None, "", [], {})}
    return meta


def fetch_rebrickable_set(set_num_or_query: str, barcode: str | None = None) -> dict[str, Any] | None:
    """Fetch LEGO set metadata from Rebrickable v3 API by set number.

    Args:
        set_num_or_query: LEGO set number (e.g., '10318' or '10318-1').
        barcode: Scanned physical EAN/UPC barcode, if available.

    Returns:
        Structured metadata dictionary or None if not found or unconfigured.
    """
    api_key = get_rebrickable_api_key()
    if not api_key:
        logger.debug("REBRICKABLE_API_KEY is not configured; skipping Rebrickable lookup.")
        return None

    normalized = normalize_set_number(set_num_or_query)
    url = f"{_REBRICKABLE_BASE_URL}/sets/{normalized}/"
    headers = {"Authorization": f"key {api_key}", "Accept": "application/json"}

    try:
        record_outbound_telemetry("rebrickable", headers, url=url)
        response = safe_get(url, headers=headers, timeout=_TIMEOUT)
        if response.status_code == 200:
            set_data = response.json()
            return _format_rebrickable_set_payload(set_data, headers, barcode=barcode)
        if response.status_code == 404:
            logger.debug("LEGO set %s not found in Rebrickable (404).", normalized)
            return None
        logger.warning("Rebrickable API returned HTTP %s for set %s.", response.status_code, normalized)
    except (requests.RequestException, SSRFError, ValueError) as exc:
        logger.warning("Rebrickable lookup failed for set %s: %s", normalized, exc)
    return None


def search_rebrickable_sets(query: str, max_results: int = 10, barcode: str | None = None) -> list[dict[str, Any]]:
    """Search Rebrickable v3 API for LEGO sets matching a text query or barcode.

    Args:
        query: Search query (name, partial number, or barcode).
        max_results: Maximum candidates to retrieve.
        barcode: Optional physical barcode to bind to results.

    Returns:
        List of formatted candidate dictionaries.
    """
    api_key = get_rebrickable_api_key()
    if not api_key:
        return []

    url = f"{_REBRICKABLE_BASE_URL}/sets/"
    headers = {"Authorization": f"key {api_key}", "Accept": "application/json"}
    params = {"search": query.strip(), "page_size": max_results}

    try:
        record_outbound_telemetry("rebrickable", headers, url=url)
        response = safe_get(url, headers=headers, params=params, timeout=_TIMEOUT)
        if response.status_code == 200:
            results = response.json().get("results", [])
            candidates: list[dict[str, Any]] = []
            for item in results[:max_results]:
                formatted = _format_rebrickable_set_payload(item, headers, barcode=barcode)
                candidates.append(formatted)
            return candidates
    except (requests.RequestException, SSRFError, ValueError) as exc:
        logger.warning("Rebrickable search failed for query '%s': %s", query, exc)
    return []


def fetch_rebrickable_metadata(identifier: str) -> dict[str, Any] | None:
    """Unified entry point for LEGO metadata lookup by set number or search phrase.

    If identifier matches set number syntax, performs direct set lookup;
    otherwise searches by text query and returns the top result with candidates.
    """
    cleaned = identifier.strip()
    if is_set_number_format(cleaned):
        set_meta = fetch_rebrickable_set(cleaned)
        if set_meta:
            return set_meta

    candidates = search_rebrickable_sets(cleaned, max_results=5)
    if candidates:
        top = dict(candidates[0])
        top["candidates"] = candidates
        return top
    return None
