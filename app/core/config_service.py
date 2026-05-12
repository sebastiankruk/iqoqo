# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>
#
"""Unified configuration service prioritizing DB overrides over environment variables."""

# pylint: disable=broad-exception-caught

import json
import os
from typing import Any


class ConfigService:
    """Service to fetch configuration values uniformly across the application.

    Priority order:
    1. Database override (InstanceSettings table)
    2. Flask app config
    3. Environment variable
    """

    @staticmethod
    def get(key: str, default: Any | None = None) -> Any | None:
        """Get config value from DB overrides, falling back to Flask config, then Environment.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            The configuration value from highest priority source
        """
        try:
            from flask import current_app

            if current_app:
                from app.db.models import InstanceSettings

                setting = InstanceSettings.query.filter_by(key=key).first()
                if setting is not None and setting.value is not None:
                    return setting.value
        except Exception:
            pass  # DB context might not be fully initialized

        try:
            from flask import current_app

            if current_app and key in current_app.config:
                return current_app.config[key]
        except Exception:
            pass

        return os.environ.get(key, default)

    @staticmethod
    def get_list(key: str, default: list | None = None) -> list:
        """Retrieve a list value, parsing JSON arrays or comma-separated strings.

        Args:
            key: Configuration key to retrieve
            default: Default list if key not found

        Returns:
            List of values from configuration
        """
        val = ConfigService.get(key)
        if val is None:
            return default if default is not None else []

        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [x.strip() for x in val.split(",") if x.strip()]
        return [val]

    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """Get a boolean config value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Boolean value from configuration
        """
        val = ConfigService.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return default
