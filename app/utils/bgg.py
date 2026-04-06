"""BoardGameGeek (BGG) metadata lookup utilities."""

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
import xml.etree.ElementTree as ET
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 15
_READ_TIMEOUT: int = 45


def fetch_bgg_metadata(query: str) -> dict[str, Any] | None:
    """Fetch board game metadata from BoardGameGeek XML API v2."""
    search_url = "https://boardgamegeek.com/xmlapi2/search"

    try:
        # Step 1: Search for the exact or closest match to get the BGG ID
        search_resp = requests.get(search_url, params={"query": query, "type": "boardgame"}, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
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
        thing_resp = requests.get(thing_url, params={"id": bgg_id}, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
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

        mechanics = [link.attrib.get("value") for link in item.findall("link[@type='boardgamemechanic']")]
        designers = [link.attrib.get("value") for link in item.findall("link[@type='boardgamedesigner']")]

        return {
            "Title": title,
            "Description": description,
            "cover_url": cover_url,
            "Mechanics": mechanics,
            "Designers": designers,
            "author": designers[0] if designers else None,
            "Format": "boardgame",
            "format": "boardgame",
            "Source": "BGG",
        }
    except (requests.RequestException, ET.ParseError) as e:
        logger.warning(f"BGG fetch failed for {query}: {e}")
        return None
