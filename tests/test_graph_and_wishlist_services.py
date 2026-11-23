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


def test_build_library_graph_multi_tier_budget_and_parts_edges(app) -> None:
    """Library mode partitions node budget across tiers and emits parts_expansions/contrib edges."""
    from app.core.graph_service import GraphService
    from app.db.contributions import Contributor, ExpressionContribution, WorkContribution, WorkPart
    from app.db.core import WorkExpansionLink

    with app.app_context():
        user = User(email="libgraph@iqoqo.local", public_username="libgraph", visibility="public")
        db.session.add(user)
        db.session.flush()

        works = [Work(title=f"Lib Work {i}", meta={}) for i in range(15)]
        db.session.add_all(works)
        db.session.flush()

        expr = Expression(work_id=works[0].id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, format="book", meta={})
        db.session.add(manif)
        db.session.flush()
        item = Item(manifestation_id=manif.id, owner_id=user.id, visibility="public", is_hidden=False)
        contrib = Contributor(name="Lib Author")
        db.session.add_all([item, contrib])
        db.session.flush()

        db.session.add_all(
            [
                WorkContribution(work_id=works[0].id, contributor_id=contrib.id, role="author"),
                ExpressionContribution(expression_id=expr.id, contributor_id=contrib.id, role="translator"),
                WorkPart(container_work_id=works[0].id, part_work_id=works[1].id, sequence=1),
                WorkExpansionLink(base_work_id=works[0].id, expansion_work_id=works[2].id, link_type="sequel"),
            ]
        )
        db.session.commit()

        # max_nodes=24 is smaller than 15 works * 2 but must NOT starve non-Work tiers
        result = GraphService.build_library_graph(max_nodes=24)
        node_types = {n["entity_type"] for n in result["nodes"]}
        assert "work" in node_types
        assert "expression" in node_types
        assert "manifestation" in node_types
        assert "item" in node_types
        assert "contributor" in node_types
        edge_rels = {e["relation"] for e in result["edges"]}
        assert "has_part" in edge_rels
        assert "expands" in edge_rels
        assert "contributed_by" in edge_rels


def test_build_neighborhood_depth4_caps_per_node_fanout(app) -> None:
    """Depth >= 3 enforces MAX_NEIGHBORS_PER_NODE_DEEP per hub expansion."""
    from app.core.graph_service import MAX_NEIGHBORS_PER_NODE_DEEP, GraphService

    with app.app_context():
        work = Work(title="Hub Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manifs = [Manifestation(expression_id=expr.id, format="book", meta={"title": f"Ed {i}"}) for i in range(35)]
        db.session.add_all(manifs)
        db.session.commit()

        graph = GraphService.build_neighborhood("expression", expr.id, depth=4, max_nodes=150)
        assert graph is not None
        manif_nodes = [n for n in graph["nodes"] if n["entity_type"] == "manifestation"]
        assert len(manif_nodes) <= MAX_NEIGHBORS_PER_NODE_DEEP


def test_federation_consent_friend_public_item_visibility(app) -> None:
    """Opted-out owner's public item remains visible to accepted friends but hidden from strangers."""
    from app.core.graph_service import GraphService
    from app.db.auth import UserFriendship
    from app.db.federation import FederationConsent

    with app.app_context():
        owner = User(email="optout_owner@iqoqo.local", public_username="optout_owner", visibility="public")
        friend = User(email="optout_friend@iqoqo.local", public_username="optout_friend", visibility="public")
        stranger = User(email="optout_stranger@iqoqo.local", public_username="optout_stranger", visibility="public")
        db.session.add_all([owner, friend, stranger])
        db.session.flush()

        db.session.add(FederationConsent(user_id=owner.id, federated_collection=False))
        db.session.add(UserFriendship(requester_id=owner.id, addressee_id=friend.id, status="accepted"))

        w = Work(title="Consent Parity Work", meta={})
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, format="book", meta={})
        db.session.add(m)
        db.session.flush()
        pub_item = Item(manifestation_id=m.id, owner_id=owner.id, visibility="public", is_hidden=False)
        fr_item = Item(manifestation_id=m.id, owner_id=owner.id, visibility="friends_only", is_hidden=False)
        db.session.add_all([pub_item, fr_item])
        db.session.commit()

        stranger_graph = GraphService.build_library_graph(entity_types={"item"}, viewer_user_id=stranger.id)
        assert [n["entity_id"] for n in stranger_graph["nodes"]] == []

        friend_graph = GraphService.build_library_graph(entity_types={"item"}, viewer_user_id=friend.id)
        assert {n["entity_id"] for n in friend_graph["nodes"]} == {pub_item.id, fr_item.id}


def test_graph_truncation_flags_on_deep_cap_and_library_tier_quota(app) -> None:
    """meta.truncated is True when deep per-node cap or library tier_quota caps results."""
    from app.core.graph_service import MAX_NEIGHBORS_PER_NODE_DEEP, GraphService

    with app.app_context():
        works = [Work(title=f"Quota Work {i}", meta={}) for i in range(15)]
        db.session.add_all(works)
        db.session.flush()
        expr = Expression(work_id=works[0].id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manifs = [Manifestation(expression_id=expr.id, format="book", meta={"title": f"Book {i}"}) for i in range(30)]
        db.session.add_all(manifs)
        db.session.commit()

        deep_graph = GraphService.build_neighborhood("expression", expr.id, depth=4, max_nodes=150)
        assert deep_graph is not None
        assert len([n for n in deep_graph["nodes"] if n["entity_type"] == "manifestation"]) <= MAX_NEIGHBORS_PER_NODE_DEEP
        assert deep_graph["meta"]["truncated"] is True

        lib_graph = GraphService.build_library_graph(entity_types={"work", "expression", "manifestation"}, max_nodes=12)
        assert lib_graph["meta"]["truncated"] is True
