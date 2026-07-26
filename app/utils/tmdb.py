"""TMDB (The Movie Database) metadata lookup utilities."""

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

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7


def clean_video_title(title: str) -> str:
    """Clean a product title by removing common format suffixes like [Blu-ray] to improve TMDB search results."""
    if not title:
        return ""
    # Take only the first part before a comma or a standalone dash to avoid UPC DB junk
    title = title.split(",")[0]
    title = title.split(" - ")[0]

    # Remove common bracketed suffixes
    title = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    # Remove common keywords like DVD, Blu-Ray, Used, etc.
    title = re.sub(r"(?i)\b(blu-ray|dvd|4k|uhd|import|widescreen|edition|steelbook|used|new|english|language|vhs)\b", "", title)

    # Collapse multiple spaces and trim
    title = re.sub(r"\s+", " ", title)
    return title.strip(" -:")


def fetch_video_metadata(query: str) -> dict[str, Any] | None:
    """Fetch video metadata from TMDB using a movie or TV show title search.

    The ``query`` value is passed directly to TMDB's ``/search/multi`` endpoint,
    so this function supports title-based lookups only. It does not resolve
    UPC, EAN, or other barcode identifiers directly.
    """
    api_key = os.environ.get("TMDB_API_KEY")
    bearer_token = os.environ.get("TMDB_API_READ_ACCESS_TOKEN")

    if not api_key and not bearer_token:
        logger.warning("TMDB_API_KEY or TMDB_API_READ_ACCESS_TOKEN is not set.")
        return None

    # TMDB multi search endpoint allows finding both TV shows and movies
    url = "https://api.themoviedb.org/3/search/multi"
    params: dict[str, str] = {"query": query}
    headers: dict[str, str] = {"Accept": "application/json"}

    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    elif api_key:
        params["api_key"] = api_key

    try:
        response = requests.get(url, params=params, headers=headers, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return None

        # Filter out person results from multi search
        results = [r for r in data["results"] if r.get("media_type") in ("movie", "tv")]
        if not results:
            return None

        best_match = results[0]
        poster_path = best_match.get("poster_path")
        media_type = best_match.get("media_type")

        # Handle differences between movie and tv schemas
        title = best_match.get("title") or best_match.get("name", "")
        release_date = best_match.get("release_date") or best_match.get("first_air_date")

        return {
            "Title": title,
            "Description": best_match.get("overview", ""),
            "cover_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
            "ReleaseDate": release_date,
            "Format": "video",
            "tmdb_media_type": media_type,
            "tmdb_id": best_match.get("id"),
            "Source": "TMDB",
            "raw_payload": best_match,
        }
    except requests.RequestException as e:
        logger.warning(f"TMDB fetch failed for {query}: {e}")
        return None
