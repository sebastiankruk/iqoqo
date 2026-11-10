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

import json
import os
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

CONFIG_KEY_BLOCKLIST: frozenset[str] = frozenset(
    {
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
    }
)


def sanitize_credential_string(val: Any) -> Any:
    """Strip whitespace and unwrap accidental surrounding single or double quotes."""
    if not isinstance(val, str):
        return val
    cleaned = val.strip()
    if len(cleaned) >= 2 and ((cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'"))):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def is_credential_or_sensitive_key(key: str) -> bool:
    """Check whether a key represents a sensitive credential, secret, token, password, or identifier."""
    if not isinstance(key, str):
        return False
    from app.db.settings import SENSITIVE_SETTING_KEYS, is_sensitive_key

    if is_sensitive_key(key) or key in SENSITIVE_SETTING_KEYS:
        return True
    return any(suffix in key for suffix in ("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_ID", "_URL", "_DATA"))


class ConfigService:
    """Service to fetch configuration values uniformly across the application.

    Priority order:
    1. Database override (InstanceSettings table)
    2. Flask app config
    3. Environment variable
    """

    CONFIG_KEY_BLOCKLIST = CONFIG_KEY_BLOCKLIST

    @staticmethod
    def get(key: str, default: Any | None = None) -> Any | None:
        """Get config value from DB overrides, falling back to Flask config, then Environment.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            The configuration value from highest priority source
        """
        raw_env = os.environ.get(key)
        is_cred = is_credential_or_sensitive_key(key)

        def _clean_val(val: Any) -> Any:
            return sanitize_credential_string(val) if is_cred else val

        if key not in CONFIG_KEY_BLOCKLIST:
            try:
                from flask import current_app

                if current_app:
                    from app.db.models import InstanceSettings

                    val = InstanceSettings.get_value(key)
                    if val is not None:
                        return _clean_val(val)
            except (SQLAlchemyError, ValueError, AttributeError, KeyError, RuntimeError):
                pass  # DB context might not be fully initialized

        # If not in DB, check os.environ if non-empty (allows test monkeypatching)
        if raw_env is not None and raw_env != "":
            return _clean_val(raw_env)

        try:
            from flask import current_app

            if current_app and current_app.config.get(key) is not None:
                return _clean_val(current_app.config[key])
        except (ValueError, AttributeError, KeyError, RuntimeError):
            pass

        if raw_env is not None:
            return _clean_val(raw_env)
        return default

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

    @staticmethod
    def get_float(key: str, default: float = 0.0) -> float:
        """Get a float config value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Float value from configuration
        """
        val = ConfigService.get(key, default)
        try:
            return float(val)
        except (TypeError, ValueError):
            return default


def is_federation_head_mode() -> bool:
    """Check whether this instance operates in read-only Federation Head mode.

    Returns:
        True if FEDERATION_HEAD_MODE is enabled in InstanceSettings, Flask config, or environment.
    """
    return ConfigService.get_bool("FEDERATION_HEAD_MODE", False)
