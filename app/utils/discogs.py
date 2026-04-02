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

    Requires DISCOGS_USER_TOKEN in environment variables.

    Args:
        barcode (str): The UPC or EAN barcode.

    Returns:
        dict | None: Dictionary containing title, author, cover_url, etc. or None if not found.
    """
    token = os.environ.get("DISCOGS_USER_TOKEN")
    if not token:
        logger.warning("DISCOGS_USER_TOKEN not set. Skipping Discogs lookup.")
        return None

    url = f"https://api.discogs.com/database/search?barcode={barcode}&type=release"
    headers = {"User-Agent": "iqoqo/0.2.0 ( dev@kruk.me )", "Authorization": f"Discogs token={token}"}

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
