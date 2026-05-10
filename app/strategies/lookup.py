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
"""
Lookup strategies for barcode and external identifier metadata retrieval.
"""

import sys
from abc import ABC, abstractmethod

from app.utils.bgg import fetch_bgg_metadata
from app.utils.discogs import fetch_discogs_by_id, fetch_discogs_metadata
from app.utils.isbn import canonicalize_isbn, fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


class LookupStrategy(ABC):
    """Base interface for media metadata lookup strategies."""

    @abstractmethod
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        """
        Look up metadata for a given barcode or query.
        Returns a tuple of (metadata_dict, provider_name).
        """
        pass


class VideoLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        upc_meta = resolve_physical_media(barcode)

        if upc_meta and upc_meta.get("title"):
            title = clean_video_title(upc_meta["title"])
            meta = fetch_video_metadata(title)
            if meta:
                meta["data_source"] = "tmdb"
                provider = "tmdb"
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

        return meta, provider


class BoardGameLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        is_short_numeric = barcode.isdigit() and len(barcode) <= 7

        if is_short_numeric:
            meta = fetch_bgg_metadata(barcode)
            if meta:
                meta["data_source"] = "bgg"
                provider = "bgg"
        else:
            upc_meta = resolve_physical_media(barcode)
            if upc_meta and upc_meta.get("title"):
                meta = fetch_bgg_metadata(upc_meta["title"])
                if meta:
                    meta["data_source"] = "bgg"
                    provider = "bgg"
                    if isinstance(meta, dict):
                        meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                else:
                    meta = upc_meta
                    meta["data_source"] = "upc"
                    provider = "upc"

            if not meta:
                meta = fetch_bgg_metadata(barcode)
                if meta:
                    meta["data_source"] = "bgg"
                    provider = "bgg"

        return meta, provider


class PuzzleLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta = resolve_physical_media(barcode)
        if meta:
            meta["data_source"] = "upc"
            return meta, "upc"
        return None, None


class AudioLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        if barcode.isdigit() and len(barcode) <= 7:
            meta = fetch_discogs_by_id(barcode)
            if meta:
                meta["data_source"] = "discogs"
                provider = "discogs"

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

        return meta, provider


class BookLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        canonical = canonicalize_isbn(barcode)
        if canonical:
            meta = fetch_isbn_metadata(canonical)
            if meta:
                meta["data_source"] = meta.get("Source", "google_books").lower().replace(" ", "_")
                provider = "isbn"

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

        return meta, provider


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


class LookupStrategyFactory:
    """Factory to retrieve the appropriate lookup strategy based on format hint."""

    @staticmethod
    def get_strategy(category_hint: str | None) -> LookupStrategy:
        """Dynamically resolve strategy based on ontology-driven LOOKUP_STRATEGY_MAP."""
        from app.core.taxonomy import LOOKUP_STRATEGY_MAP

        if not category_hint:
            return DefaultFallbackStrategy()

        strategy_class_name: str | None = LOOKUP_STRATEGY_MAP.get(category_hint)
        if not strategy_class_name:
            return DefaultFallbackStrategy()

        strategy_class = getattr(sys.modules[__name__], strategy_class_name, None)
        if strategy_class and issubclass(strategy_class, LookupStrategy):
            import typing

            return typing.cast(LookupStrategy, strategy_class())

        return DefaultFallbackStrategy()
