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
"""Federation guard decorator — disables federation endpoints when feature is off."""

from __future__ import annotations

from functools import wraps

from flask import jsonify


def federation_required(f):
    """Decorator that returns 404 if federation is not enabled.

    Checks the FEDERATION_ENABLED config value (supports runtime toggle
    via ConfigService / InstanceSettings).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        from app.core.config_service import ConfigService

        enabled = ConfigService.get("FEDERATION_ENABLED", False)
        if isinstance(enabled, str):
            enabled = enabled.lower() in {"true", "1", "yes"}

        if not enabled:
            return jsonify({"error": "Federation is not enabled"}), 404
        return f(*args, **kwargs)

    return decorated
