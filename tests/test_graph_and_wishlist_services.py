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
"""Direct unit tests for app.core.graph_service and app.core.wishlist_service."""

import uuid

from app.core.graph_service import MAX_GRAPH_DEPTH, MAX_GRAPH_NODES, GraphService, is_item_visible_to_viewer
from app.core.wishlist_service import fulfill_wishlist_intent_for_manifestation, upsert_wishlist_intent_for_manifestation
from app.db.models import Expression, Item, Manifestation, User, UserWorkIntent, Work, db


def test_graph_service_visibility_and_depth_bounds(app) -> None:
    """Verify is_item_visible_to_viewer and build_catalog_graph enforce visibility and depth bounds."""
    with app.app_context():
        owner = User(email="g_owner@iqoqo.local", public_username="g_owner", visibility="public")
        friend = User(email="g_friend@iqoqo.local", public_username="g_friend", visibility="public")
        stranger = User(email="g_stranger@iqoqo.local", public_username="g_stranger", visibility="public")
        db.session.add_all([owner, friend, stranger])
        db.session.flush()

        work = Work(title="Graph Service Unit Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, format="paperback", meta={})
        db.session.add(manif)
        db.session.flush()

        public_item = Item(manifestation_id=manif.id, owner_id=owner.id, visibility="public", is_hidden=False, status="unread")
        friends_item = Item(manifestation_id=manif.id, owner_id=owner.id, visibility="friends_only", is_hidden=True, status="unread")
        private_item = Item(manifestation_id=manif.id, owner_id=owner.id, visibility="private", is_hidden=True, status="unread")
        db.session.add_all([public_item, friends_item, private_item])
        db.session.commit()

        assert is_item_visible_to_viewer(public_item, None, set()) is True
        assert is_item_visible_to_viewer(friends_item, friend.id, {owner.id}) is True
        assert is_item_visible_to_viewer(friends_item, stranger.id, set()) is False
        assert is_item_visible_to_viewer(private_item, owner.id, set()) is True
        assert is_item_visible_to_viewer(private_item, friend.id, {owner.id}) is False
        assert is_item_visible_to_viewer(private_item, "invalid-uuid", set()) is False

        graph = GraphService.build_neighborhood(
            "expression",
            expr.id,
            depth=MAX_GRAPH_DEPTH + 3,
            max_nodes=MAX_GRAPH_NODES + 50,
            viewer_user_id=stranger.id,
        )
        assert graph is not None
        assert graph["meta"]["depth"] == MAX_GRAPH_DEPTH
        assert graph["meta"]["max_nodes"] == MAX_GRAPH_NODES
        item_nodes = [n for n in graph["nodes"] if n["entity_type"] == "item"]
        assert len(item_nodes) == 1
        assert item_nodes[0]["entity_id"] == public_item.id


def test_wishlist_service_upsert_and_fulfill(app) -> None:
    """Verify upsert_wishlist_intent_for_manifestation creates/updates intents and fulfill removes them."""
    with app.app_context():
        user = User(email="wl_unit@iqoqo.local", public_username="wl_unit", visibility="public")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Wishlist Service Unit Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="audio")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, format="cd", meta={})
        db.session.add(manif)
        db.session.commit()

        intent = upsert_wishlist_intent_for_manifestation(user.id, manif)
        assert intent is not None
        assert intent.work_id == work.id
        assert intent.manifestation_id == manif.id
        assert intent.status == "want_to_listen"

        updated = upsert_wishlist_intent_for_manifestation(user.id, manif, status="listening", is_hidden=True)
        assert updated is not None
        assert updated.id == intent.id
        assert updated.status == "listening"
        assert updated.is_hidden is True

        removed = fulfill_wishlist_intent_for_manifestation(user.id, manif)
        db.session.flush()
        assert removed == 1
        assert db.session.get(UserWorkIntent, intent.id) is None
        assert fulfill_wishlist_intent_for_manifestation(uuid.uuid4(), manif) == 0
