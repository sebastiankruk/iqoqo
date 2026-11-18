"""OpenCollections.org lookup strategy for federated cultural/media metadata."""

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from app.strategies.base import LookupStrategy
from app.utils.opencollections import fetch_opencollections_record, search_opencollections_candidates


class OpenCollectionsLookupStrategy(LookupStrategy):
    """Lookup strategy querying OpenCollections.org via SSRF-safe HTTP client."""

    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        """Resolve metadata by identifier/barcode or fallback search query."""
        if barcode and barcode.strip():
            record = fetch_opencollections_record(barcode)
            if record is not None:
                return record, "opencollections"

        if query and query.strip():
            candidates = search_opencollections_candidates(query, max_results=1)
            if candidates:
                return candidates[0], "opencollections"

        return None, None

    def lookup_candidates(self, query: str, max_results: int = 10) -> list[dict]:
        """Search OpenCollections.org for candidate metadata dictionaries."""
        return search_opencollections_candidates(query, max_results=max_results)
