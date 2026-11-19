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
"""Tests for bounded, visibility-safe Catalog Relation Graph API (C133)."""

from app.api.auth import generate_internal_jwt
from app.db.models import (
    ContainerAggregation,
    Contributor,
    Expression,
    Item,
    Manifestation,
    SemanticLink,
    User,
    UserFriendship,
    Work,
    WorkContribution,
    WorkExpansionLink,
    WorkPart,
    WorkSeriesMembership,
    db,
)


def _auth_header(user: User) -> dict[str, str]:
    token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


def test_catalog_graph_traverses_relations_and_enforces_visibility(app, client):
    """Verify FRBR, series, parts, expansions, contributors, maps, accepted LOD, and Item privacy."""
    with app.app_context():
        owner = User(email="graph_owner@iqoqo.local", public_username="graph_owner", visibility="public")
        friend = User(email="graph_friend@iqoqo.local", public_username="graph_friend", visibility="public")
        stranger = User(email="graph_stranger@iqoqo.local", public_username="graph_stranger", visibility="public")
        db.session.add_all([owner, friend, stranger])
        db.session.flush()

        db.session.add(UserFriendship(requester_id=owner.id, addressee_id=friend.id, status="accepted"))

        # Anchor Work + Series + Part + Expansion + ContainerAggregation
        series_work = Work(title="Middle-earth Legendarium", work_kind="series", meta={})
        main_work = Work(title="The Fellowship of the Ring", meta={"authors": ["J.R.R. Tolkien"]})
        part_work = Work(title="Book One: The Ring Sets Out", meta={})
        expansion_work = Work(title="The Black Riders Expansion", meta={})
        rulebook_work = Work(title="Companion Map Booklet", meta={})
        db.session.add_all([series_work, main_work, part_work, expansion_work, rulebook_work])
        db.session.flush()

        db.session.add(WorkSeriesMembership(work_id=main_work.id, series_work_id=series_work.id, sequence=1))
        db.session.add(WorkPart(container_work_id=main_work.id, part_work_id=part_work.id, sequence=1))
        db.session.add(WorkExpansionLink(base_work_id=main_work.id, expansion_work_id=expansion_work.id))
        db.session.add(
            ContainerAggregation(
                container_work_id=main_work.id,
                aggregated_type="work",
                aggregated_work_id=rulebook_work.id,
                component_name="Companion Booklet",
                quantity=1,
            )
        )

        author = Contributor(name="J.R.R. Tolkien", type="person")
        db.session.add(author)
        db.session.flush()
        db.session.add(WorkContribution(work_id=main_work.id, contributor_id=author.id, role="author", sequence=0))

        # Approved vs pending LOD links
        accepted_lod = SemanticLink(
            entity_type="work",
            entity_id=main_work.id,
            authority="dbpedia",
            external_uri="https://dbpedia.org/resource/The_Fellowship_of_the_Ring",
            pref_label="The Fellowship of the Ring",
            status="accepted",
        )
        pending_lod = SemanticLink(
            entity_type="work",
            entity_id=main_work.id,
            authority="wordnet",
            external_uri="https://wordnet-rdf.princeton.edu/id/99999999-n",
            pref_label="Unapproved Guess",
            status="pending",
        )
        db.session.add_all([accepted_lod, pending_lod])

        expr = Expression(work_id=main_work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(
            expression_id=expr.id,
            format_type="hardcover",
            publisher="Allen & Unwin",
            meta={
                "format": "hardcover",
                "map_attachments": [
                    {
                        "id": "map-me-1",
                        "title": "Thror's Map Foldout",
                        "type": "fold_out_insert",
                        "scale": "1:1000000",
                        "image_url": "https://example.com/map.jpg",
                    }
                ],
            },
        )
        db.session.add(man)
        db.session.flush()

        public_item = Item(owner_id=owner.id, manifestation_id=man.id, status="read", visibility="public")
        friends_item = Item(owner_id=owner.id, manifestation_id=man.id, status="reading", visibility="friends_only")
        private_item = Item(owner_id=owner.id, manifestation_id=man.id, status="unread", visibility="private")
        db.session.add_all([public_item, friends_item, private_item])
        db.session.commit()

        main_work_id = main_work.id
        man_id = man.id
        public_id = public_item.id
        friends_id = friends_item.id
        private_id = private_item.id
        owner_hdr = _auth_header(owner)
        friend_hdr = _auth_header(friend)
        stranger_hdr = _auth_header(stranger)

    # 1. Depth=2 around Work includes FRBR, series, part, expansion, container agg, contributor, accepted LOD
    res_work = client.get(f"/api/catalog/graph?entity_type=work&entity_id={main_work_id}&depth=2")
    assert res_work.status_code == 200
    body = res_work.get_json()["data"]
    node_ids = {n["id"] for n in body["nodes"]}
    relations = {e["relation"] for e in body["edges"]}

    assert f"work:{main_work_id}" in node_ids
    assert f"manifestation:{man_id}" in node_ids
    assert {"realizes", "embodies", "in_series", "has_part", "is_expansion_of", "contributed_by", "same_as"} <= relations
    assert f"lod:{accepted_lod.id}" in node_ids
    # Pending SemanticLink must never leak
    assert all(n.get("label") != "Unapproved Guess" for n in body["nodes"])

    # 2. Item visibility enforcement anchored on Manifestation (depth=1 shows Items and Maps)
    anon_res = client.get(f"/api/catalog/graph?entity_type=manifestation&entity_id={man_id}&depth=1")
    assert anon_res.status_code == 200
    anon_data = anon_res.get_json()["data"]
    anon_ids = {n["id"] for n in anon_data["nodes"]}
    assert f"item:{public_id}" in anon_ids
    assert f"item:{friends_id}" not in anon_ids
    assert f"item:{private_id}" not in anon_ids
    assert f"map:{man_id}:map-me-1" in anon_ids

    stranger_res = client.get(
        f"/api/catalog/graph?entity_type=manifestation&entity_id={man_id}&depth=1",
        headers=stranger_hdr,
    )
    stranger_ids = {n["id"] for n in stranger_res.get_json()["data"]["nodes"]}
    assert f"item:{public_id}" in stranger_ids
    assert f"item:{friends_id}" not in stranger_ids
    assert f"item:{private_id}" not in stranger_ids

    friend_res = client.get(
        f"/api/catalog/graph?entity_type=manifestation&entity_id={man_id}&depth=1",
        headers=friend_hdr,
    )
    friend_ids = {n["id"] for n in friend_res.get_json()["data"]["nodes"]}
    assert f"item:{public_id}" in friend_ids
    assert f"item:{friends_id}" in friend_ids
    assert f"item:{private_id}" not in friend_ids

    owner_res = client.get(
        f"/api/catalog/graph?entity_type=manifestation&entity_id={man_id}&depth=1",
        headers=owner_hdr,
    )
    owner_ids = {n["id"] for n in owner_res.get_json()["data"]["nodes"]}
    assert {f"item:{public_id}", f"item:{friends_id}", f"item:{private_id}"} <= owner_ids

    # 3. Direct private item anchor blocked for non-owners (404), allowed for owner (200)
    assert client.get(f"/api/catalog/graph?entity_type=item&entity_id={private_id}").status_code == 404
    assert client.get(f"/api/catalog/graph?entity_type=item&entity_id={private_id}", headers=friend_hdr).status_code == 404
    assert client.get(f"/api/catalog/graph?entity_type=item&entity_id={private_id}", headers=owner_hdr).status_code == 200


def test_catalog_graph_clamping_filtering_and_validation(app, client):
    """Verify depth clamping, max_nodes truncation flag, edge_types filtering, and input validation."""
    with app.app_context():
        work = Work(title="Prolific Serial", work_kind="serial", issn="1507-5966", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="pl")
        db.session.add(expr)
        db.session.flush()
        for idx in range(1, 10):
            db.session.add(Manifestation(expression_id=expr.id, issue_number=str(idx), publication_year=2004))
        c = Contributor(name="Serial Editor", type="person")
        db.session.add(c)
        db.session.flush()
        db.session.add(WorkContribution(work_id=work.id, contributor_id=c.id, role="editor", sequence=0))
        db.session.commit()
        work_id = work.id

    # Clamped depth=99 -> 2 and max_nodes=4 triggers truncated=True
    res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={work_id}&depth=99&max_nodes=4")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["meta"]["depth"] == 2
    assert len(data["nodes"]) == 4
    assert data["meta"]["truncated"] is True

    # edge_types=contributors returns only anchor + contributor
    contrib_res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={work_id}&depth=2&edge_types=contributors")
    assert contrib_res.status_code == 200
    contrib_data = contrib_res.get_json()["data"]
    assert {n["entity_type"] for n in contrib_data["nodes"]} == {"work", "contributor"}
    assert all(e["category"] == "contributors" for e in contrib_data["edges"])

    # Invalid parameters return clean 400/404 JSON envelopes
    assert client.get("/api/catalog/graph?entity_type=invalid&entity_id=1").status_code == 400
    assert client.get(f"/api/catalog/graph?entity_type=work&entity_id={work_id}&edge_types=bogus").status_code == 400
    assert client.get("/api/catalog/graph?entity_type=work&entity_id=0").status_code == 400
    assert client.get("/api/catalog/graph?entity_type=work&entity_id=999999").status_code == 404
