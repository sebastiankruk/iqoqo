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
import copy
import logging

import requests

from app.strategies.base import LookupStrategy
from app.utils.allegro import fetch_allegro_candidates, fetch_allegro_metadata
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import canonicalize_isbn, fetch_google_books_candidates, fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata

logger = logging.getLogger(__name__)


class BookLookupStrategy(LookupStrategy):
    """Lookup strategy for Books / Text media format."""

    def lookup_candidates(self, query: str, max_results: int = 10) -> list[dict]:
        """Aggregate candidate books from Google Books and Allegro up to max_results."""
        candidates: list[dict] = []
        try:
            gb_candidates = fetch_google_books_candidates(query, max_results=max_results)
            candidates.extend(gb_candidates)
            if len(candidates) < max_results:
                allegro_candidates = fetch_allegro_candidates(query, max_results=max_results - len(candidates))
                candidates.extend(allegro_candidates)
        except (requests.RequestException, ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError) as exc:
            logger.error(f"Book strategy candidates lookup failed: {exc}")

        return candidates[:max_results]

    def lookup(self, barcode: str, query: str | None = None, max_results: int = 10) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        try:
            canonical = canonicalize_isbn(barcode)
            if canonical:
                meta = fetch_isbn_metadata(canonical)
                if meta:
                    meta["data_source"] = meta.get("Source", "google_books").lower().replace(" ", "_")
                    provider = "isbn"

            if not meta and not canonical:
                search_term = query or barcode
                candidates = self.lookup_candidates(search_term, max_results=max_results)
                if candidates:
                    meta = copy.deepcopy(candidates[0])
                    meta["candidates"] = candidates
                    provider = meta.get("data_source", "google_books")

            if not meta:
                meta = fetch_allegro_metadata(barcode)
                if meta:
                    meta["data_source"] = "allegro"
                    provider = "allegro"

            if not meta:
                meta = fetch_discogs_metadata(barcode)
                if meta:
                    meta["data_source"] = "discogs"
                    provider = "discogs"

            if not meta:
                meta = fetch_audio_metadata(barcode)
                if meta:
                    meta["data_source"] = "musicbrainz"
                    provider = "musicbrainz"
        except (requests.RequestException, ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError) as exc:
            logger.error(f"Strategy lookup failed: {exc}")

        return meta, provider
