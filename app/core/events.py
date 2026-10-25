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
"""Server-Sent Events (SSE) and real-time transition pub/sub pipeline.

Decouples write operations from client notifications and coordinates
real-time cache invalidation across web clients using Redis PubSub
with automatic fallback to thread-safe in-process queues.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)

REDIS_EVENTS_CHANNEL = "iqoqo:events"

# Thread-safe in-process subscriber queues for tests and Redis-less runtimes
_in_process_subscribers: list[queue.Queue[dict[str, Any]]] = []
_subscribers_lock = threading.Lock()


def get_redis_client():
    """Retrieve connected Redis client or return None on connection failure."""
    redis_url = None
    if current_app:
        redis_url = current_app.config.get("REDIS_URL")
    if not redis_url:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:
        logger.debug("Redis unavailable for events pub/sub: %s", exc)
        return None


def publish_transition_event(event_type: str, payload: dict[str, Any]) -> None:
    """Broadcast an entity transition or background indexing event.

    Args:
        event_type: Identifier of the event (e.g., 'item_updated', 'fts_reindexed').
        payload: Event payload dictionary with entity references and metadata.
    """
    message = {
        "event": event_type,
        "data": payload,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    encoded = json.dumps(message)

    # 1. Distribute via Redis Pub/Sub if available
    client = get_redis_client()
    if client:
        try:
            client.publish(REDIS_EVENTS_CHANNEL, encoded)
        except Exception as exc:
            logger.warning("Failed to publish event to Redis: %s", exc)

    # 2. Always distribute to in-process subscribers (for unit tests and local SSE)
    with _subscribers_lock:
        stale_queues: list[queue.Queue[dict[str, Any]]] = []
        for q in _in_process_subscribers:
            try:
                q.put_nowait(message)
            except queue.Full:
                stale_queues.append(q)
        for sq in stale_queues:
            if sq in _in_process_subscribers:
                _in_process_subscribers.remove(sq)


def _should_deliver_event(event_dict: dict[str, Any], user_id: str | None) -> bool:
    """Check if a transition event should be delivered to a given subscriber.

    User-scoped events ('item_created', 'item_updated', 'item_deleted', 'custody_lent',
    'custody_returned') are delivered only to the owner or borrower. System and catalog
    events are delivered to all subscribers. If user_id is None (e.g. in unit tests),
    all events are delivered.
    """
    if user_id is None:
        return True
    event_type = event_dict.get("event")
    user_scoped_events = {"item_created", "item_updated", "item_deleted", "custody_lent", "custody_returned"}
    if event_type not in user_scoped_events:
        return True

    data = event_dict.get("data")
    if not isinstance(data, dict):
        return True

    allowed_ids = {
        str(data.get("user_id")) if data.get("user_id") is not None else None,
        str(data.get("owner_id")) if data.get("owner_id") is not None else None,
        str(data.get("borrower_id")) if data.get("borrower_id") is not None else None,
    }
    allowed_ids.discard(None)
    return str(user_id) in allowed_ids


def subscribe_events(timeout_seconds: float = 30.0, user_id: str | None = None) -> Generator[str, None, None]:
    """Yield Server-Sent Events formatted strings from Redis or local in-process queue.

    Args:
        timeout_seconds: Maximum total streaming duration per SSE connection.
        user_id: Authenticated user ID to filter private user transitions.

    Yields:
        Formatted SSE event strings (e.g., 'data: {...}\\n\\n' or ': ping\\n\\n').
    """
    start_time = time.time()
    last_ping = start_time

    # Attempt Redis Pub/Sub connection first
    client = get_redis_client()
    if client:
        try:
            pubsub = client.pubsub()
            pubsub.subscribe(REDIS_EVENTS_CHANNEL)
            yield ": connected\n\n"

            try:
                while time.time() - start_time < timeout_seconds:
                    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg and msg.get("type") == "message":
                        raw_data = msg.get("data")
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8")
                        try:
                            parsed = json.loads(raw_data)
                            if isinstance(parsed, dict) and not _should_deliver_event(parsed, user_id):
                                continue
                        except Exception:
                            pass
                        yield f"data: {raw_data}\n\n"
                        last_ping = time.time()
                    elif time.time() - last_ping >= 15.0:
                        yield ": ping\n\n"
                        last_ping = time.time()
                return
            finally:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("Redis subscription failed, falling back to in-process subscriber: %s", exc)
            try:
                client.close()
            except Exception:
                pass

    # Fallback to in-process queue
    local_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
    with _subscribers_lock:
        _in_process_subscribers.append(local_queue)

    yield ": connected\n\n"

    try:
        while time.time() - start_time < timeout_seconds:
            try:
                event_data = local_queue.get(timeout=1.0)
                if _should_deliver_event(event_data, user_id):
                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_ping = time.time()
            except queue.Empty:
                if time.time() - last_ping >= 15.0:
                    yield ": ping\n\n"
                    last_ping = time.time()
    finally:
        with _subscribers_lock:
            if local_queue in _in_process_subscribers:
                _in_process_subscribers.remove(local_queue)
