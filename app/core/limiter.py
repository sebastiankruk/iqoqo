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
"""Rate limiter configuration."""

from flask import g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_user_id_or_ip():
    """Use authenticated user ID for rate limiting, fallback to IP."""
    user_id = getattr(g, "user_id", None)
    if user_id is not None:
        return str(user_id)
    return get_remote_address()


limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Default to memory, but app init will override with Redis
)


@limiter.request_filter
def exempt_metrics():
    """Exempt prometheus metrics endpoint from rate limiting."""
    return request.path == "/metrics"
