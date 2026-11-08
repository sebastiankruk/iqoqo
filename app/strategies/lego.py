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
from app.utils.allegro import fetch_allegro_candidates, fetch_allegro_metadata
from app.utils.rebrickable import (
    fetch_rebrickable_metadata,
    fetch_rebrickable_set,
    is_set_number_format,
    search_rebrickable_sets,
)
from app.utils.upc import resolve_physical_media

logger = logging.getLogger(__name__)


def _extract_set_number_from_title(title: str) -> str | None:
    """Extract a 4-7 digit LEGO set number from a title string.

    Avoids capturing 4-digit calendar years (1990..2035) when other
    candidates exist or when the 4-digit number is plausibly a release year.
    Prefers 5-6 digit tokens over 4-digit tokens.
    """
    if not title:
        return None
    tokens = re.findall(r"\b(\d{4,7})\b", title)
    if not tokens:
        return None
    non_years: list[str] = []
    possible_years: list[str] = []
    for tok in tokens:
        if len(tok) == 4 and 1990 <= int(tok) <= 2035:
            possible_years.append(tok)
        else:
            non_years.append(tok)

    if non_years:
        five_to_six = [t for t in non_years if 5 <= len(t) <= 6]
        if five_to_six:
            return five_to_six[0]
        return non_years[0]
    return possible_years[0]


class LegoLookupStrategy(LookupStrategy):
    """LEGO sets lookup via Rebrickable API, Allegro retail fallback, and EAN/UPC barcode resolution."""

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

                # 2b. Allegro retail product fallback for European/Polish LEGO barcodes
                allegro_meta = fetch_allegro_metadata(cleaned_barcode)
                if allegro_meta and allegro_meta.get("title"):
                    meta = allegro_meta.copy()
                    meta["category"] = "lego"
                    meta["format"] = "standard_set"
                    meta["data_source"] = "allegro"
                    provider = "allegro"

                    # Try to extract set number from parameters or title
                    set_num = meta.get("set_number")
                    if not set_num and meta.get("title"):
                        extracted = _extract_set_number_from_title(meta["title"])
                        if extracted:
                            set_num = extracted
                            meta["set_number"] = set_num

                    # Enrich with Rebrickable if set number found and Rebrickable is configured
                    if set_num:
                        try:
                            reb_meta = fetch_rebrickable_set(set_num, barcode=cleaned_barcode)
                            if reb_meta:
                                if not meta.get("piece_count") and reb_meta.get("piece_count"):
                                    meta["piece_count"] = reb_meta["piece_count"]
                                if not meta.get("minifig_count") and reb_meta.get("minifig_count"):
                                    meta["minifig_count"] = reb_meta["minifig_count"]
                                if not meta.get("theme") and reb_meta.get("theme"):
                                    meta["theme"] = reb_meta["theme"]
                                if not meta.get("cover_url") and reb_meta.get("cover_url"):
                                    meta["cover_url"] = reb_meta["cover_url"]
                        except Exception as exc:
                            logger.debug("Rebrickable enrichment skipped for set %s: %s", set_num, exc)

                    return meta, provider

                # 2c. Fallback to UPC database waterfall
                upc_meta = resolve_physical_media(cleaned_barcode)
                if upc_meta and upc_meta.get("title"):
                    title = upc_meta["title"]
                    # Extract 4-7 digit set number from product title if present (e.g. 'LEGO 10318 Concorde')
                    set_num = _extract_set_number_from_title(title)
                    if set_num:
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

                # Query Allegro for candidates if Rebrickable returned nothing
                allegro_cands = fetch_allegro_candidates(cleaned_query, max_results=1)
                if allegro_cands:
                    meta = allegro_cands[0].copy()
                    meta["category"] = "lego"
                    meta["format"] = "standard_set"
                    meta["data_source"] = "allegro"
                    provider = "allegro"
                    return meta, provider

        except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError) as exc:
            logger.warning("Unexpected error during LEGO lookup for '%s': %s", barcode, exc)

        return None, None

    def lookup_candidates(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Look up multiple candidate metadata dictionaries for a LEGO set query from Rebrickable and Allegro."""
        candidates: list[dict[str, Any]] = []
        try:
            reb_cands = search_rebrickable_sets(query, max_results=max_results)
            candidates.extend(reb_cands)
        except Exception as exc:
            logger.warning("Error searching Rebrickable LEGO candidates for '%s': %s", query, exc)

        if len(candidates) < max_results:
            try:
                allegro_cands = fetch_allegro_candidates(query, max_results=max_results - len(candidates))
                for c in allegro_cands:
                    c.setdefault("category", "lego")
                    c.setdefault("format", "standard_set")
                    c.setdefault("data_source", "allegro")
                    candidates.append(c)
            except Exception as exc:
                logger.warning("Error searching Allegro LEGO candidates for '%s': %s", query, exc)

        return candidates[:max_results]
