"""BoardGameGeek (BGG) metadata lookup utilities.

Implementation note: This module uses raw HTTP requests to the BGG XML API v2 rather than
the `boardgamegeek2` PyPI library. Reason: the library does not support custom Authorization
headers (required for BGG_API_TOKEN), and our response dict maps to FRBR-specific keys
(`Title`, `Designers`, `PublicationYear`, `Source`, `Format`) that would need a new mapping
layer over the library's objects. Migration to `boardgamegeek2` is tracked for a future release.
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
import xml.etree.ElementTree as ET
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7


def get_bgg_headers() -> dict[str, str]:
    """Get the headers required for calling BoardGameGeek XML API v2."""
    headers = {"User-Agent": "iqoqo/0.3.0 (https://github.com/sebastiankruk/iqoqo)", "Accept": "application/xml"}

    token = os.getenv("BGG_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def clean_bgg_query(query: str) -> str:
    """Removes parenthetical metadata from query for better BGG matching."""
    if not query:
        return ""
    import re

    # Strip (Year), [Edition], (Big Box) etc
    cleaned = re.sub(r"[\(\[].*?[\)\]]", "", query)
    return " ".join(cleaned.split()).strip()


def fetch_bgg_metadata(query: str) -> dict[str, Any] | None:
    """Fetch board game metadata from BoardGameGeek XML API v2."""
    search_url = "https://boardgamegeek.com/xmlapi2/search"

    token = os.getenv("BGG_API_TOKEN")
    if not token:
        logger.warning("BGG_API_TOKEN not found in environment. BoardGameGeek lookups will likely result in 401 Unauthorized.")

    headers = get_bgg_headers()

    # Step 0: Clean query — BGG search performs much better without parenthetical years
    # e.g., "Brass: Pittsburgh (2027)" -> "Brass: Pittsburgh"
    cleaned_query = clean_bgg_query(query)

    try:
        # Step 1: Search for the exact or closest match to get the BGG ID
        # We use the cleaned query for searching
        search_resp = requests.get(
            search_url,
            params={"query": cleaned_query, "type": "boardgame"},
            headers=headers,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        search_resp.raise_for_status()

        search_root = ET.fromstring(search_resp.content)
        first_item = search_root.find("item")

        if first_item is None:
            return None

        bgg_id = first_item.attrib.get("id")
        if not bgg_id:
            return None

        # Step 2: Fetch detailed metadata for the retrieved ID
        thing_url = "https://boardgamegeek.com/xmlapi2/thing"
        thing_resp = requests.get(thing_url, params={"id": bgg_id}, headers=headers, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        thing_resp.raise_for_status()

        thing_root = ET.fromstring(thing_resp.content)
        item = thing_root.find("item")

        if item is None:
            return None

        name_elem = item.find("name[@type='primary']")
        title = name_elem.attrib.get("value") if name_elem is not None else "Unknown"

        desc_elem = item.find("description")
        description = desc_elem.text if desc_elem is not None else ""

        img_elem = item.find("image")
        cover_url = img_elem.text if img_elem is not None else None

        minplayers_elem = item.find("minplayers")
        min_players = int(minplayers_elem.attrib.get("value", 0)) if minplayers_elem is not None else None

        maxplayers_elem = item.find("maxplayers")
        max_players = int(maxplayers_elem.attrib.get("value", 0)) if maxplayers_elem is not None else None

        playingtime_elem = item.find("playingtime")
        playing_time = int(playingtime_elem.attrib.get("value", 0)) if playingtime_elem is not None else None

        yearpublished_elem = item.find("yearpublished")
        year_published = yearpublished_elem.attrib.get("value") if yearpublished_elem is not None else None

        mechanics = [link.attrib.get("value") for link in item.findall("link[@type='boardgamemechanic']")]
        designers = [link.attrib.get("value") for link in item.findall("link[@type='boardgamedesigner']")]

        return {
            "Title": title,
            "Description": description,
            "cover_url": cover_url,
            "Mechanics": mechanics,
            "Designers": designers,
            "author": designers[0] if designers else None,
            "min_players": min_players,
            "max_players": max_players,
            "playing_time": playing_time,
            "PublicationYear": year_published,
            "bgg_id": bgg_id,
            "Format": "boardgame",
            "format": "boardgame",
            "Source": "BGG",
            "raw_payload": {"bgg_id": bgg_id, "xml": thing_resp.text},
        }
    except (requests.RequestException, ET.ParseError, ValueError, KeyError) as e:
        logger.warning(f"BGG fetch failed for {query}: {e}")
        return None
