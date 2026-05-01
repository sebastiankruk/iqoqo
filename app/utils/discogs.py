"""Handles Discogs API lookups for audio items."""

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

import requests

logger = logging.getLogger(__name__)


def _normalize_release_data(release: dict) -> dict:
    """Helper to convert Discogs release JSON into iqoqo metadata format."""
    # Discogs format: "Artist - Title"
    title_raw = release.get("title", "Unknown Artist - Unknown Title")
    parts = title_raw.split(" - ", 1)
    artist = parts[0] if len(parts) > 1 else "Unknown Artist"
    title = parts[1] if len(parts) > 1 else title_raw

    publisher = release.get("label", [None])[0] if isinstance(release.get("label"), list) else release.get("label")
    cover_url = release.get("cover_image") or release.get("thumb")

    # Determine specific format. Discogs search results provide a "format" list of strings,
    # while /releases/{id} provides a "formats" list of objects.
    format_labels = []

    search_formats = release.get("format", [])
    if isinstance(search_formats, str):
        format_labels.append(search_formats)
    elif isinstance(search_formats, list):
        format_labels.extend(item for item in search_formats if isinstance(item, str))

    release_formats = release.get("formats", [])
    if isinstance(release_formats, list):
        for item in release_formats:
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str):
                    format_labels.append(name)
                # Expand descriptions if present
                descriptions = item.get("descriptions", [])
                if isinstance(descriptions, str):
                    format_labels.append(descriptions)
                elif isinstance(descriptions, list):
                    format_labels.extend(desc for desc in descriptions if isinstance(desc, str))
            elif isinstance(item, str):
                format_labels.append(item)

    media_format = (
        "vinyl" if any(label == "Vinyl" for label in format_labels) else "cd" if any(label == "CD" for label in format_labels) else "audio"
    )

    return {
        "title": title,
        "author": artist,
        "publisher": publisher,
        "cover_url": cover_url,
        "format": media_format,
        "language": "en",
        "discogs_id": str(release.get("id")),
    }


def fetch_discogs_metadata(barcode: str) -> dict | None:
    """Fetch metadata for an audio item using its barcode from Discogs.

    Supports two authentication methods (priority fallback):
    1. Preferred: DISCOGS_CONSUMER_KEY and DISCOGS_CONSUMER_SECRET (OAuth 1.0a consumer key/secret).
    2. Legacy: DISCOGS_USER_TOKEN (Personal Access Token).

    Args:
        barcode (str): The UPC or EAN barcode.

    Returns:
        dict | None: Dictionary containing title, author, cover_url, etc. or None if not found.
    """
    consumer_key = os.environ.get("DISCOGS_CONSUMER_KEY")
    consumer_secret = os.environ.get("DISCOGS_CONSUMER_SECRET")
    legacy_token = os.environ.get("DISCOGS_USER_TOKEN")

    if consumer_key and consumer_secret:
        # Preferred: OAuth 1.0a consumer credentials
        auth_header = f"Discogs key={consumer_key}, secret={consumer_secret}"
    elif legacy_token:
        # Fallback: legacy personal access token (still valid, just deprecated)
        logger.debug("Using legacy DISCOGS_USER_TOKEN; consider migrating to DISCOGS_CONSUMER_KEY/SECRET.")
        auth_header = f"Discogs token={legacy_token}"
    else:
        logger.warning("No Discogs credentials found. Skipping Discogs lookup.")
        return None

    from app.config import Config

    url = "https://api.discogs.com/database/search"
    params = {"barcode": barcode, "type": "release"}
    headers = {"User-Agent": f"iqoqo/{Config.VERSION} ( info@iqoqo.cc )", "Authorization": auth_header}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return None

        release = data["results"][0]
        return _normalize_release_data(release)

    except requests.RequestException as e:
        logger.error(f"Failed to fetch Discogs metadata for {barcode}: {e}")
        return None


def fetch_discogs_candidates(query: str, max_results: int = 5) -> list[dict]:
    """Search Discogs by text query and return up to max_results normalised candidates.

    Used for disambiguation when searching by artist/title rather than a barcode.

    Args:
        query (str): Free-text search term (e.g. ``"Stachura – SDM*"``).
        max_results (int): Maximum number of results to return (default 5).

    Returns:
        list[dict]: List of normalised release metadata dicts, possibly empty.
    """
    consumer_key = os.environ.get("DISCOGS_CONSUMER_KEY")
    consumer_secret = os.environ.get("DISCOGS_CONSUMER_SECRET")
    legacy_token = os.environ.get("DISCOGS_USER_TOKEN")

    if consumer_key and consumer_secret:
        auth_header = f"Discogs key={consumer_key}, secret={consumer_secret}"
    elif legacy_token:
        auth_header = f"Discogs token={legacy_token}"
    else:
        logger.warning("No Discogs credentials found. Skipping Discogs candidate search.")
        return []

    from app.config import Config

    url = "https://api.discogs.com/database/search"
    params = {"q": query, "type": "release"}
    headers = {"User-Agent": f"iqoqo/{Config.VERSION} ( info@iqoqo.cc )", "Authorization": auth_header}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        return [_normalize_release_data(r) for r in results[:max_results]]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Discogs candidates for '{query}': {e}")
        return []


def fetch_discogs_by_id(discogs_id: str) -> dict | None:
    """Fetch metadata for an audio item using its Discogs Release ID.

    Args:
        discogs_id (str): The Discogs release ID.

    Returns:
        dict | None: Dictionary containing title, author, cover_url, etc. or None if not found.
    """
    consumer_key = os.environ.get("DISCOGS_CONSUMER_KEY")
    consumer_secret = os.environ.get("DISCOGS_CONSUMER_SECRET")
    legacy_token = os.environ.get("DISCOGS_USER_TOKEN")

    if consumer_key and consumer_secret:
        auth_header = f"Discogs key={consumer_key}, secret={consumer_secret}"
    elif legacy_token:
        auth_header = f"Discogs token={legacy_token}"
    else:
        return None

    from app.config import Config

    url = f"https://api.discogs.com/releases/{discogs_id}"
    headers = {"User-Agent": f"iqoqo/{Config.VERSION} ( info@iqoqo.cc )", "Authorization": auth_header}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        release = response.json()

        # Releases endpoint sometimes has artists and labels as nested objects
        normalized = _normalize_release_data(release)

        # Fix artists if they come from the 'artists' array
        artists = release.get("artists", [])
        if artists:
            normalized["author"] = artists[0].get("name", normalized["author"])

        # Fix labels
        labels = release.get("labels", [])
        if labels:
            normalized["publisher"] = labels[0].get("name", normalized["publisher"])

        return normalized

    except requests.RequestException as e:
        logger.error(f"Failed to fetch Discogs metadata for ID {discogs_id}: {e}")
        return None
