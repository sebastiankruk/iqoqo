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
from abc import ABC, abstractmethod


class LookupStrategy(ABC):
    """Base interface for media metadata lookup strategies."""

    @abstractmethod
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        """
        Look up metadata for a given barcode or query.
        Returns a tuple of (metadata_dict, provider_name).
        """
        pass

    def lookup_candidates(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Look up multiple candidate metadata dictionaries for a title or query string.
        Returns a list of candidate dictionaries.
        """
        return []
