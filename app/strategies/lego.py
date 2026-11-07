"""LEGO set metadata lookup via Rebrickable and UPC/EAN resolution."""

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
import re
from typing import Any

from app.strategies.base import LookupStrategy
from app.utils.rebrickable import (
    fetch_rebrickable_metadata,
    fetch_rebrickable_set,
    is_set_number_format,
    search_rebrickable_sets,
)
from app.utils.upc import resolve_physical_media

logger = logging.getLogger(__name__)


class LegoLookupStrategy(LookupStrategy):
    """LEGO sets lookup via Rebrickable API and EAN/UPC barcode resolution."""

    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
        """Look up LEGO set metadata by set number, EAN/UPC barcode, or title query."""
        meta: dict[str, Any] | None = None
        provider: str | None = None

        try:
            cleaned_barcode = barcode.strip()

            # 1. Direct LEGO Set Number lookup (e.g., '10318' or '10318-1')
            if is_set_number_format(cleaned_barcode):
                meta = fetch_rebrickable_set(cleaned_barcode)
                if meta:
                    provider = "rebrickable"
                    return meta, provider

            # 2. Physical EAN/UPC Barcode resolution
            is_barcode_number = cleaned_barcode.isdigit() and len(cleaned_barcode) in (8, 12, 13, 14)
            if is_barcode_number:
                # 2a. Direct search in Rebrickable for barcode
                candidates = search_rebrickable_sets(cleaned_barcode, max_results=1, barcode=cleaned_barcode)
                if candidates:
                    meta = candidates[0]
                    provider = "rebrickable"
                    return meta, provider

                # 2b. Fallback to UPC database waterfall
                upc_meta = resolve_physical_media(cleaned_barcode)
                if upc_meta and upc_meta.get("title"):
                    title = upc_meta["title"]
                    # Extract 4-6 digit set number from product title if present (e.g. 'LEGO 10318 Concorde')
                    match = re.search(r"\b(\d{4,6})\b", title)
                    if match:
                        set_num = match.group(1)
                        meta = fetch_rebrickable_set(set_num, barcode=cleaned_barcode)
                        if meta:
                            provider = "rebrickable"
                            return meta, provider

                    # Search Rebrickable by UPC title
                    candidates = search_rebrickable_sets(title, max_results=1, barcode=cleaned_barcode)
                    if candidates:
                        meta = candidates[0]
                        provider = "rebrickable"
                        return meta, provider

            # 3. Fallback to query string lookup if barcode did not match
            if not meta and query:
                cleaned_query = query.strip()
                if is_set_number_format(cleaned_query):
                    meta = fetch_rebrickable_set(cleaned_query)
                else:
                    meta = fetch_rebrickable_metadata(cleaned_query)

                if meta:
                    provider = "rebrickable"
                    return meta, provider

        except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError) as exc:
            logger.warning("Unexpected error during LEGO lookup for '%s': %s", barcode, exc)

        return None, None

    def lookup_candidates(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Look up multiple candidate metadata dictionaries for a LEGO set query."""
        try:
            return search_rebrickable_sets(query, max_results=max_results)
        except Exception as exc:
            logger.warning("Error searching LEGO candidates for '%s': %s", query, exc)
            return []
