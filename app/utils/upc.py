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

"""Universal UPC/EAN metadata fetcher for retail items like Puzzles."""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def fetch_upc_metadata(barcode: str) -> dict | None:
    """Fetch product metadata using a universal UPC API (e.g., UPCitemdb)."""
    api_key = os.getenv("UPC_ITEM_DB_KEY")
    try:
        if api_key:
            url = f"https://api.upcitemdb.com/prod/v1/lookup?upc={barcode}"
            response = requests.get(url, headers={"user_key": api_key, "Accept": "application/json"}, timeout=5)
        else:
            # Fallback to trial endpoint (no key required, limited rate)
            url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
            response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("items") and len(data["items"]) > 0:
                item = data["items"][0]
                return {
                    "title": item.get("title", "Unknown Puzzle"),
                    "barcode": item.get("upc") or item.get("ean"),
                    "cover_url": item.get("images", [None])[0],
                    "description": item.get("description"),
                    "manufacturer": item.get("brand"),
                    "format": "puzzle",
                    "publisher": item.get("brand"),
                }
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("UPC lookup failed for barcode %s", barcode)
    return None
