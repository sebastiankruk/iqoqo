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

"""Jigsaw Puzzle models (catalog schema).

Implements FRBRoo mapping for Jigsaw Puzzles.
- F1 Work: Original Artwork / Illustration
- F3 Manifestation: Specific manufacturer's cut (e.g., 1000 pieces Ravensburger)
- F5 Item: The physical puzzle box
"""

from __future__ import annotations

MANIFESTATION_PUZZLE_META_KEYS: tuple[str, ...] = ("piece_count", "dimensions", "artist", "manufacturer", "puzzle_type")
