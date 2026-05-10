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
from app.strategies.base import LookupStrategy
from app.utils.bgg import fetch_bgg_metadata
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import canonicalize_isbn, fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


class DefaultFallbackStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None

        # Prioritize ISBN for ISBN-like barcodes (original scanner behavior)
        is_isbn_like = len(barcode) == 13 and (barcode.startswith("978") or barcode.startswith("979")) or len(barcode) == 10
        if is_isbn_like:
            canonical = canonicalize_isbn(barcode)
            if canonical:
                meta = fetch_isbn_metadata(canonical)
                if meta:
                    meta["data_source"] = meta.get("Source", "google_books").lower().replace(" ", "_")
                    provider = "isbn"
                    return meta, provider

        # Otherwise follow general waterfall
        meta = fetch_discogs_metadata(barcode)
        if meta:
            meta["data_source"] = "discogs"
            provider = "discogs"

        if not meta:
            meta = fetch_audio_metadata(barcode)
            if meta:
                meta["data_source"] = "musicbrainz"
                provider = "musicbrainz"

        if not meta and not is_isbn_like:  # Don't double check if already tried above
            canonical = canonicalize_isbn(barcode)
            if canonical:
                meta = fetch_isbn_metadata(canonical)
                if meta:
                    meta["data_source"] = meta.get("Source", "google_books").lower().replace(" ", "_")
                    provider = "isbn"

        if not meta:
            upc_meta = resolve_physical_media(barcode)
            if upc_meta and upc_meta.get("title"):
                title = clean_video_title(upc_meta["title"])
                meta = fetch_video_metadata(title)
                if meta:
                    meta["data_source"] = "tmdb"
                    provider = "tmdb"
                    meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                else:
                    meta = fetch_bgg_metadata(upc_meta["title"])
                    if meta:
                        meta["data_source"] = "bgg"
                        provider = "bgg"
                        meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                    else:
                        meta = upc_meta
                        provider = "upc"
                        meta["data_source"] = "upc"

            if not meta:
                meta = fetch_video_metadata(barcode)
                if meta:
                    meta["data_source"] = "tmdb"
                    provider = "tmdb"
                else:
                    meta = fetch_bgg_metadata(barcode)
                    if meta:
                        meta["data_source"] = "bgg"
                        provider = "bgg"

        return meta, provider
