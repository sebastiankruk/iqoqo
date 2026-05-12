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
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


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
