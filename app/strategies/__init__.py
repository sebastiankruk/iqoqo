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

from .audio import AudioLookupStrategy
from .base import LookupStrategy
from .boardgame import BoardGameLookupStrategy
from .book import BookLookupStrategy
from .default import DefaultFallbackStrategy
from .factory import LookupStrategyFactory
from .puzzle import PuzzleLookupStrategy
from .video import VideoLookupStrategy

__all__ = [
    "LookupStrategy",
    "VideoLookupStrategy",
    "BoardGameLookupStrategy",
    "PuzzleLookupStrategy",
    "AudioLookupStrategy",
    "BookLookupStrategy",
    "DefaultFallbackStrategy",
    "LookupStrategyFactory",
]
