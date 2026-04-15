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

    url = f"https://api.discogs.com/database/search?barcode={barcode}&type=release"
    headers = {"User-Agent": "iqoqo/0.4.0 ( dev@kruk.me )", "Authorization": auth_header}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return None

        release = data["results"][0]

        # Discogs format: "Artist - Title"
        title_raw = release.get("title", "Unknown Artist - Unknown Title")
        parts = title_raw.split(" - ", 1)
        artist = parts[0] if len(parts) > 1 else "Unknown Artist"
        title = parts[1] if len(parts) > 1 else title_raw

        publisher = release.get("label", [None])[0]
        cover_url = release.get("cover_image")

        # Determine specific format
        formats = release.get("format", [])
        media_format = "vinyl" if "Vinyl" in formats else "cd" if "CD" in formats else "audio"

        return {"title": title, "author": artist, "publisher": publisher, "cover_url": cover_url, "format": media_format, "language": "en"}
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Discogs metadata for {barcode}: {e}")
        return None
