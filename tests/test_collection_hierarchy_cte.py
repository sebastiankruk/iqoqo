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
"""Tests for recursive-CTE collection hierarchy traversal and cycle detection.

Validates multi-level ancestor resolution, cross-tenant isolation, recursion
bounding, and that cycle detection now costs a constant number of round-trips
rather than one per hierarchy level.
"""

import jwt
import pytest
from sqlalchemy import event

from app.api.collections import MAX_HIERARCHY_DEPTH, get_collection_hierarchy_ids
from app.db.core import UserCollection, db
from app.db.models import User


def _auth_headers(app, user):
    token = jwt.encode({"sub": str(user.id)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def chain_setup(app):
    """Build a 5-level collection chain: L0 > L1 > L2 > L3 > L4 (L4 deepest)."""
    with app.app_context():
        user = User(email="cte_test@example.com", display_name="CTE Tester")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        ids = []
        parent_id = None
        for level in range(5):
            col = UserCollection(owner_id=user.id, name=f"Level{level}", parent_id=parent_id)
            db.session.add(col)
            db.session.flush()
            ids.append(col.id)
            parent_id = col.id

        db.session.commit()
        return {
            "user_id": user.id,
            "headers": _auth_headers(app, user),
            "root": ids[0],
            "levels": ids,
        }


# ── Ancestor resolution ────────────────────────────────────────────────


def test_ancestors_of_root_is_empty(client, chain_setup, app):
    with app.app_context():
        assert get_collection_hierarchy_ids(chain_setup["root"], chain_setup["user_id"]) == {chain_setup["root"]}


def test_ancestors_resolves_all_levels(client, chain_setup, app):
    """A 5-deep chain must resolve every ancestor, nearest parent first."""
    with app.app_context():
        deepest = chain_setup["levels"][-1]
        hierarchy = get_collection_hierarchy_ids(deepest, chain_setup["user_id"])
        assert hierarchy == set(chain_setup["levels"])


def test_ancestors_of_single_child_is_just_parent(client, chain_setup, app):
    with app.app_context():
        assert get_collection_hierarchy_ids(chain_setup["levels"][1], chain_setup["user_id"]) == {
            chain_setup["root"],
            chain_setup["levels"][1],
        }


def test_ancestors_of_unknown_id_is_empty(client, chain_setup, app):
    with app.app_context():
        assert get_collection_hierarchy_ids(999_999, chain_setup["user_id"]) == set()


# ── Cross-tenant isolation (IDOR) ──────────────────────────────────────


def test_ancestors_do_not_leak_across_users(client, chain_setup, app):
    """A user must not be able to resolve another user's hierarchy."""
    with app.app_context():
        other = User(email="cte_other@example.com", display_name="Other")
        other.set_password("Pass123!")
        db.session.add(other)
        db.session.flush()

        deepest = chain_setup["levels"][-1]
        assert get_collection_hierarchy_ids(deepest, other.id) == set()


def test_cannot_reparent_into_another_users_collection(client, chain_setup, app):
    """A parent's hierarchy is scoped to its owner, so cross-user ids 400."""
    with app.app_context():
        other = User(email="cte_other2@example.com", display_name="Other2")
        other.set_password("Pass123!")
        db.session.add(other)
        db.session.flush()

        foreign = UserCollection(owner_id=other.id, name="Foreign")
        db.session.add(foreign)
        db.session.commit()
        foreign_id = foreign.id

    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": foreign_id},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert "Invalid parent collection" in resp.get_json()["error"]


# ── Cycle detection via the API ────────────────────────────────────────


def test_cannot_set_own_parent(client, chain_setup):
    col_id = chain_setup["levels"][2]
    resp = client.put(f"/api/collections/{col_id}", json={"parent_id": col_id}, headers=chain_setup["headers"])
    assert resp.status_code == 400
    assert "own parent" in resp.get_json()["error"]


def test_cannot_create_direct_cycle(client, chain_setup):
    """Making the root a child of its own descendant is a cycle."""
    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": chain_setup["levels"][3]},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert "Circular reference" in resp.get_json()["error"]


def test_cannot_create_transitive_cycle(client, chain_setup):
    """Cycle detection must work through several levels, not just one hop."""
    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": chain_setup["levels"][-1]},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert "Circular reference" in resp.get_json()["error"]


def test_deep_cycle_is_detected(client, app, chain_setup):
    """A cycle at the very top of a deep chain is still caught."""
    with app.app_context():
        # Extend the chain to 8 levels and try to fold it back to the top.
        parent_id = chain_setup["levels"][-1]
        for i in range(3):
            col = UserCollection(owner_id=chain_setup["user_id"], name=f"Deep{i}", parent_id=parent_id)
            db.session.add(col)
            db.session.flush()
            parent_id = col.id
        db.session.commit()

    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": parent_id},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert "Circular reference" in resp.get_json()["error"]


def test_valid_reparent_is_allowed(client, app, chain_setup):
    """A sibling subtree may be moved under an unrelated parent."""
    with app.app_context():
        side = UserCollection(owner_id=chain_setup["user_id"], name="SideA")
        db.session.add(side)
        db.session.flush()
        side_id = side.id

        branch = UserCollection(owner_id=chain_setup["user_id"], name="SideB", parent_id=side_id)
        db.session.add(branch)
        db.session.commit()
        branch_id = branch.id

    resp = client.put(
        f"/api/collections/{branch_id}",
        json={"parent_id": chain_setup["root"]},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 200
    assert resp.get_json()["collection"]["parent_id"] == chain_setup["root"]


def test_unknown_parent_rejected(client, chain_setup):
    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": 999_999},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert "Invalid parent collection" in resp.get_json()["error"]


# ── Round-trip efficiency (single query, bounded recursion) ────────────


def test_ancestor_traversal_uses_a_single_query(client, chain_setup, app):
    """The whole ancestor walk must cost one round-trip, regardless of depth."""
    statements = []

    def _record(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        statements.append(statement)

    with app.app_context():
        event.listen(db.engine, "before_cursor_execute", _record)
        try:
            hierarchy = get_collection_hierarchy_ids(chain_setup["levels"][-1], chain_setup["user_id"])
        finally:
            event.remove(db.engine, "before_cursor_execute", _record)

    assert len(statements) == 1, f"expected exactly one query, got: {statements}"
    assert "WITH RECURSIVE" in statements[0].upper()
    assert hierarchy == set(chain_setup["levels"])


def test_recursion_terminates_on_pre_existing_cycle(client, app, chain_setup):
    """A cycle already present in the data must not hang the walk.

    The CTE uses a de-duplicating UNION, so each (id, parent_id) pair is
    expanded once and the traversal terminates. The cycle is then reported
    rather than silently treated as a valid hierarchy.
    """
    with app.app_context():
        looped = UserCollection(owner_id=chain_setup["user_id"], name="Loop", parent_id=chain_setup["root"])
        db.session.add(looped)
        db.session.commit()
        looped_id = looped.id

        # Close the cycle: root's parent is "Loop", whose parent is root.
        root = db.session.get(UserCollection, chain_setup["root"])
        root.parent_id = looped_id
        db.session.commit()

        statements = []

        def _record(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", _record)
        try:
            with pytest.raises(ValueError):
                get_collection_hierarchy_ids(chain_setup["root"], chain_setup["user_id"])
        finally:
            event.remove(db.engine, "before_cursor_execute", _record)

    # Terminates after a single query rather than looping.
    assert len(statements) == 1, statements


def test_over_deep_hierarchy_is_rejected(client, app, chain_setup):
    """An ancestor chain deeper than MAX_HIERARCHY_DEPTH is treated as corrupt.

    Builds a tower whose *ancestors* of the deepest node exceed the cap.
    """
    with app.app_context():
        # Build upward: each new node becomes the parent of the previous one.
        current_id = chain_setup["levels"][-1]
        for i in range(MAX_HIERARCHY_DEPTH + 5):
            col = UserCollection(owner_id=chain_setup["user_id"], name=f"Tower{i}", parent_id=None)
            db.session.add(col)
            db.session.flush()
            child = db.session.get(UserCollection, current_id)
            child.parent_id = col.id
            current_id = col.id
        db.session.commit()
        _ = current_id
        tower_base_id = chain_setup["levels"][-1]

        with pytest.raises(ValueError):
            get_collection_hierarchy_ids(tower_base_id, chain_setup["user_id"])

    # The API surfaces corrupt data as a 400 rather than a 500.  The parent
    # candidate is the node whose own ancestor chain exceeds the cap.
    resp = client.put(
        f"/api/collections/{chain_setup['root']}",
        json={"parent_id": tower_base_id},
        headers=chain_setup["headers"],
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False
