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


class LookupStrategyFactory:
    """Factory to retrieve the appropriate lookup strategy based on format hint."""

    @staticmethod
    def get_strategy(category_hint: str | None) -> LookupStrategy:
        """Dynamically resolve strategy based on ontology-driven LOOKUP_STRATEGY_MAP."""
        from app.core.taxonomy import LOOKUP_STRATEGY_MAP
        from app.strategies.default import DefaultFallbackStrategy

        if not category_hint:
            return DefaultFallbackStrategy()

        strategy_class_name: str | None = LOOKUP_STRATEGY_MAP.get(category_hint)
        if not strategy_class_name:
            return DefaultFallbackStrategy()

        # Dynamically find the class in the subclasses of LookupStrategy
        for cls in LookupStrategy.__subclasses__():
            if cls.__name__ == strategy_class_name:
                return cls()  # type: ignore[abstract]

        return DefaultFallbackStrategy()
