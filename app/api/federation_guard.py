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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Federation guard decorator ensuring federation feature is enabled."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import current_app, jsonify

from app.db.settings import InstanceSettings


def is_federation_enabled() -> bool:
    """Check whether federation is enabled in application config or instance settings.

    Returns:
        True if federation is enabled, False otherwise.
    """
    if current_app:
        app_cfg = current_app.config.get("FEDERATION_ENABLED")
        if app_cfg is not None:
            if isinstance(app_cfg, bool):
                return app_cfg
            return str(app_cfg).lower() in {"true", "1", "yes"}
        if current_app.config.get("TESTING"):
            return True

    # Also check InstanceSettings DB if present
    db_val = InstanceSettings.get_value("FEDERATION_ENABLED", None)
    if db_val is not None:
        if isinstance(db_val, bool):
            return db_val
        return str(db_val).lower() in {"true", "1", "yes"}

    try:
        from app.config import Config

        cfg_enabled = getattr(Config, "FEDERATION_ENABLED", False)
        if isinstance(cfg_enabled, bool):
            return cfg_enabled
        return str(cfg_enabled).lower() in {"true", "1", "yes"}
    except Exception:
        return False


def federation_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to gate federation endpoints behind FEDERATION_ENABLED check.

    Returns 404 when federation is disabled.
    """

    @wraps(func)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not is_federation_enabled():
            return jsonify({"error": "Federation is disabled on this instance", "code": 404}), 404
        return func(*args, **kwargs)

    return decorated_function
