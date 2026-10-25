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
"""Server-Sent Events (SSE) transition event stream.

Provides real-time updates for entity transitions and background
FTS reindexing so frontend caches can be invalidated reactively without polling.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Generator

from flask import Blueprint, Response, current_app, g, request, stream_with_context

from app.api.decorators import require_auth
from app.core.events import subscribe_events

logger = logging.getLogger(__name__)

events_bp = Blueprint("events", __name__, url_prefix="/api/v1/events")


@events_bp.route("/stream", methods=["GET"])
@require_auth
def stream_events() -> Response:
    """Stream real-time transition and background FTS events via Server-Sent Events (SSE).

    Clients receive real-time JSON payloads upon entity transitions (status, custody,
    FTS reindexing completion) to invalidate local client caches without polling.
    """
    try:
        raw_timeout = float(request.args.get("timeout", 30.0))
        if not math.isfinite(raw_timeout):
            timeout = 30.0
        else:
            min_bound = 0.1 if current_app and current_app.testing else 1.0
            timeout = max(min_bound, min(raw_timeout, 60.0))
    except (ValueError, TypeError):
        timeout = 30.0

    user_id = str(g.user_id) if getattr(g, "user_id", None) else None

    def generate() -> Generator[str, None, None]:
        yield f"data: {json.dumps({'event': 'connected', 'status': 'connected'})}\n\n"
        yield from subscribe_events(timeout_seconds=timeout, user_id=user_id)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
