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
"""Tests for Server-Sent Events (SSE) transition stream endpoint."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.api.auth import generate_internal_jwt
from app.core.events import publish_transition_event
from app.db import db
from app.db.models import Permission, Role, User


@pytest.fixture
def auth_user(app):
    """Seed test user and generate token."""
    with app.app_context():
        user = User(
            email="sse_user@iqoqo.local",
            display_name="SSE User",
            public_username="sseuser",
        )
        db.session.add(user)
        db.session.commit()
        token = generate_internal_jwt(user)
        return {"user_id": user.id, "token": token}


def test_sse_endpoint_requires_auth(client):
    """Verify GET /api/v1/events/stream rejects unauthenticated requests with 401."""
    res = client.get("/api/v1/events/stream")
    assert res.status_code == 401


def test_sse_endpoint_headers_and_connected_event(client, auth_user):
    """Verify SSE endpoint returns text/event-stream headers and initial connected event."""
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res = client.get("/api/v1/events/stream?timeout=0.1", headers=headers)
    try:
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type
        assert res.headers.get("Cache-Control") == "no-cache"

        data = res.get_data(as_text=True)
        assert "data: " in data
        assert "connected" in data
    finally:
        res.close()


def test_sse_endpoint_rejects_token_query_parameter(client, auth_user):
    """Verify SSE endpoint rejects token in query string to prevent credential leaking in URLs."""
    res = client.get(f"/api/v1/events/stream?token={auth_user['token']}&timeout=0.1")
    try:
        assert res.status_code == 401
    finally:
        res.close()


def test_publish_transition_event_delivers_to_subscriber(app):
    """Verify publish_transition_event broadcasts to in-process subscribers and respects user isolation."""
    from app.core.events import subscribe_events

    with app.app_context():
        # Generator subscription with authenticated user
        stream = subscribe_events(timeout_seconds=2.0, user_id="user-999")
        try:
            # Advance to initial yield so subscription is active
            init_chunk = next(stream)
            assert ": connected" in init_chunk

            # Publish event
            publish_transition_event("item_updated", {"item_id": 999, "user_id": "user-999", "status": "read"})

            # Next item yielded should be the published event
            chunk = next(stream)
            assert "data: " in chunk
            parsed = json.loads(chunk.replace("data: ", "").strip())
            assert parsed["event"] == "item_updated"
            assert parsed["data"]["item_id"] == 999
        finally:
            stream.close()


def test_sse_user_isolation_and_timeout_bounds(app, client, auth_user):
    """Verify user-scoped events are filtered to owner/borrower and timeout is clamped."""
    from app.core.events import subscribe_events

    with app.app_context():
        stream_a = subscribe_events(timeout_seconds=2.0, user_id="user-a")
        stream_b = subscribe_events(timeout_seconds=2.0, user_id="user-b")
        try:
            assert ": connected" in next(stream_a)
            assert ": connected" in next(stream_b)

            # 1. Publish private item event for user-a
            publish_transition_event("item_created", {"item_id": 101, "user_id": "user-a"})

            chunk_a = next(stream_a)
            assert "data: " in chunk_a
            parsed_a = json.loads(chunk_a.replace("data: ", "").strip())
            assert parsed_a["event"] == "item_created"
            assert parsed_a["data"]["user_id"] == "user-a"

            # 2. Publish global event
            publish_transition_event("fts_reindexed", {"entity_type": "item", "id": 101})

            chunk_b = next(stream_b)
            assert "data: " in chunk_b
            parsed_b = json.loads(chunk_b.replace("data: ", "").strip())
            # user-b must receive fts_reindexed directly, skipping user-a's private item_created
            assert parsed_b["event"] == "fts_reindexed"
        finally:
            stream_a.close()
            stream_b.close()

    # 3. Requesting unbounded / non-finite timeout via HTTP endpoint is handled safely
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    res_inf = client.get("/api/v1/events/stream?timeout=inf", headers=headers)
    try:
        assert res_inf.status_code == 200
    finally:
        res_inf.close()

    res_huge = client.get("/api/v1/events/stream?timeout=999999", headers=headers)
    try:
        assert res_huge.status_code == 200
    finally:
        res_huge.close()
