"""Handles MusicBrainz API lookups for audio items."""

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

import requests

logger = logging.getLogger(__name__)

#: MusicBrainz media ``format`` values (case-insensitive) that identify a
#: Blu-ray Pure Audio carrier.  Mirrors
#: :data:`app.strategies.audio.BLURAY_AUDIO_RAW_LABELS`.
_BLURAY_AUDIO_FORMATS: frozenset[str] = frozenset(
    {
        "blu-ray",
        "blu-ray audio",
        "bd-a",
        "blu-ray pure audio",
    }
)


def _detect_media_format(release: dict) -> str:
    """Return the canonical audio format for a MusicBrainz release.

    Reads the release's ``media`` list and maps Blu-ray carriers to
    ``bluray_audio``; otherwise falls back to the generic ``audio`` marker
    (which the read-time normalizer resolves via ``shared/format_mappings.yaml``).
    """
    media = release.get("media") or []
    for medium in media:
        if not isinstance(medium, dict):
            continue
        fmt = medium.get("format")
        if isinstance(fmt, str) and fmt.strip().lower() in _BLURAY_AUDIO_FORMATS:
            return "bluray_audio"
    return "audio"


def fetch_audio_metadata(barcode: str) -> dict | None:
    """Fetch metadata for an audio item using its barcode from MusicBrainz.

    Args:
        barcode (str): The UPC or EAN barcode.

    Returns:
        dict | None: Dictionary containing title, author, cover_url, etc. or None if not found.
    """
    url = f"https://musicbrainz.org/ws/2/release/?query=barcode:{barcode}&fmt=json"
    headers = {"User-Agent": "iqoqo/0.3.0 ( dev@kruk.me )"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("releases"):
            return None

        release = data["releases"][0]
        title = release.get("title", "Unknown Title")

        # Extract artist
        artist = "Unknown Artist"
        if release.get("artist-credit"):
            artist = release["artist-credit"][0].get("name", artist)

        # Extract publisher/label
        publisher = None
        if release.get("label-info"):
            publisher = release["label-info"][0].get("label", {}).get("name")

        # Try fetching from Cover Art Archive
        release_id = release.get("id")
        cover_url = f"https://coverartarchive.org/release/{release_id}/front" if release_id else None

        return {
            "title": title,
            "author": artist,
            "publisher": publisher,
            "cover_url": cover_url,
            "format": _detect_media_format(release),
            "language": "en",  # Defaulting, as MusicBrainz language tags are complex
        }
    except requests.RequestException as e:
        logger.error(f"Failed to fetch audio metadata for {barcode}: {e}")
        return None
