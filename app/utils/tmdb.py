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
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 15
_READ_TIMEOUT: int = 45


def fetch_video_metadata(query: str) -> dict[str, Any] | None:
    """Fetch video metadata from TMDB using a movie title search.

    The ``query`` value is passed directly to TMDB's ``/search/movie`` endpoint,
    so this function supports title-based lookups only. It does not resolve
    UPC, EAN, or other barcode identifiers.
    """
    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        logger.warning("TMDB_API_KEY is not set.")
        return None

    # TMDB find endpoint can search external IDs, but search/movie is often more robust
    # if the external ID is not explicitly indexed. We use search as a reliable catch-all.
    url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": api_key, "query": query}

    try:
        response = requests.get(url, params=params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return None

        best_match = data["results"][0]
        poster_path = best_match.get("poster_path")

        return {
            "Title": best_match.get("title", ""),
            "Description": best_match.get("overview", ""),
            "cover_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
            "ReleaseDate": best_match.get("release_date"),
            "Format": "video",
            "Source": "TMDB",
        }
    except requests.RequestException as e:
        logger.warning(f"TMDB fetch failed for {query}: {e}")
        return None
