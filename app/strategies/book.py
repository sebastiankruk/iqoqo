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
import requests

from app.strategies.base import LookupStrategy
from app.utils.allegro import fetch_allegro_metadata
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import canonicalize_isbn, fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata


class BookLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        try:
            canonical = canonicalize_isbn(barcode)
            if canonical:
                meta = fetch_isbn_metadata(canonical)
                if meta:
                    meta["data_source"] = meta.get("Source", "google_books").lower().replace(" ", "_")
                    provider = "isbn"

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
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            IndexError,
            AttributeError,
            TypeError,
            OSError,
            RuntimeError,
            Exception,
        ) as exc:
            import logging

            logging.getLogger(__name__).error(f"Strategy lookup failed: {exc}")

        return meta, provider
