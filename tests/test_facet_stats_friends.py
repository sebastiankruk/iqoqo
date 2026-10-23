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
"""Tests for friend-scoped faceted navigation statistics."""

from __future__ import annotations

import pytest

from app.api.auth import generate_internal_jwt
from app.core.data_manager import DataManager
from app.db.auth import User, UserFriendship
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import Permission, Role, db


@pytest.fixture
def social_network_data(app):
    """Seed network with User A, User B (friend), User C (stranger)."""
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)

        perm = Permission.query.filter_by(name="write:item").first()
        if not perm:
            perm = Permission(name="write:item")
            db.session.add(perm)
        if perm not in role.permissions:
            role.permissions.append(perm)

        # User A (caller)
        user_a = User(
            email="collector_a@iqoqo.local",
            public_username="collector_a",
            display_name="Collector A",
            visibility="public",
        )
        user_a.roles.append(role)

        # User B (Friend of A)
        user_b = User(
            email="collector_b@iqoqo.local",
            public_username="collector_b",
            display_name="Collector B",
            visibility="public",
        )
        user_b.roles.append(role)

        # User C (Stranger)
        user_c = User(
            email="collector_c@iqoqo.local",
            public_username="collector_c",
            display_name="Collector C",
            visibility="public",
        )
        user_c.roles.append(role)

        db.session.add_all([user_a, user_b, user_c])
        db.session.flush()

        # Mutual friendship between A and B
        friendship = UserFriendship(
            requester_id=user_a.id,
            addressee_id=user_b.id,
            status="accepted",
        )
        db.session.add(friendship)

        # Catalog entities
        work1 = Work(title="SciFi Masterpiece")
        work2 = Work(title="Fantasy Epic")
        db.session.add_all([work1, work2])
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="book")
        expr2 = Expression(work_id=work2.id, content_type="audiobook")
        db.session.add_all([expr1, expr2])
        db.session.flush()

        manif1 = Manifestation(expression_id=expr1.id, publisher="Tor Books", meta={"format": "book"})
        manif2 = Manifestation(expression_id=expr2.id, publisher="Audible", meta={"format": "audiobook_digital"})
        db.session.add_all([manif1, manif2])
        db.session.flush()

        # Item 1: Owned by A (paperback book)
        item_a = Item(owner_id=user_a.id, manifestation_id=manif1.id, status="available", is_hidden=False, visibility="public")

        # Item 2: Owned by B (friend) - visible (paperback book)
        item_b1 = Item(owner_id=user_b.id, manifestation_id=manif1.id, status="available", is_hidden=False, visibility="friends_only")

        # Item 3: Owned by B (friend) - hidden (audiobook) -> should be excluded from friend facet counts
        item_b2 = Item(owner_id=user_b.id, manifestation_id=manif2.id, status="available", is_hidden=True, visibility="private")

        # Item 4: Owned by C (stranger) - visible (audiobook) -> should be excluded from friend facet counts
        item_c = Item(owner_id=user_c.id, manifestation_id=manif2.id, status="available", is_hidden=False, visibility="public")

        db.session.add_all([item_a, item_b1, item_b2, item_c])
        db.session.commit()

        return {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
            "user_c_id": user_c.id,
            "user_a": user_a,
            "user_b": user_b,
            "user_c": user_c,
        }


def test_faceted_stats_scope_friends_includes_only_friends_visible_items(client, app, social_network_data):
    """Scenario: Facet stats with scope=friends aggregates only visible items owned by confirmed friends."""
    with app.app_context():
        user_a = db.session.get(User, social_network_data["user_a_id"])
        token = generate_internal_jwt(user_a)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/stats/facets?scope=friends", headers=headers)
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]

    # Category counts: User B has 1 visible book (item_b1) and 1 hidden audiobook (item_b2).
    # User C has an audiobook, but C is not a friend.
    # Therefore, category_counts should have 'book': 1, and 'audiobook' should not be present (or 0).
    assert data["category_counts"].get("book") == 1
    assert data["category_counts"].get("audiobook", 0) == 0

    # Format counts: format 'book' should be 1 (from item_b1), 'audiobook_digital' should not be present
    assert data["format_counts"].get("book") == 1
    assert data["format_counts"].get("audiobook_digital", 0) == 0


def test_faceted_stats_scope_own_includes_only_caller_items(client, app, social_network_data):
    """Scenario: Facet stats with scope=own aggregates caller's personal inventory."""
    with app.app_context():
        user_a = db.session.get(User, social_network_data["user_a_id"])
        token = generate_internal_jwt(user_a)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/stats/facets?scope=own", headers=headers)
    assert response.status_code == 200

    payload = response.get_json()
    data = payload["data"]

    # User A owns 1 book (item_a)
    assert data["category_counts"].get("book") == 1
    assert data["category_counts"].get("audiobook", 0) == 0


def test_faceted_stats_scope_all_includes_all_catalog_items(client, app, social_network_data):
    """Scenario: Facet stats with scope=all aggregates all items across the catalog."""
    with app.app_context():
        user_a = db.session.get(User, social_network_data["user_a_id"])
        token = generate_internal_jwt(user_a)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/stats/facets?scope=all", headers=headers)
    assert response.status_code == 200

    payload = response.get_json()
    data = payload["data"]

    # In catalog: item_a (book), item_b1 (book), item_b2 (audiobook), item_c (audiobook)
    assert data["category_counts"].get("book") == 2
    assert data["category_counts"].get("audiobook") == 2


def test_faceted_stats_scope_friends_without_friends_returns_empty(client, app, social_network_data):
    """Scenario: Caller without friends receives zero counts on scope=friends."""
    with app.app_context():
        user_c = db.session.get(User, social_network_data["user_c_id"])
        token = generate_internal_jwt(user_c)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/stats/facets?scope=friends", headers=headers)
    assert response.status_code == 200

    payload = response.get_json()
    data = payload["data"]

    # User C has no friends, so all counts are 0/empty
    assert sum(data["category_counts"].values()) == 0
    assert sum(data["format_counts"].values()) == 0
