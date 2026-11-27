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
    lod_uris = {n.get("external_uri") for n in body["nodes"] if n["entity_type"] == "lod"}
    assert "https://dbpedia.org/resource/The_Fellowship_of_the_Ring" in lod_uris
    assert all(n["id"].startswith("lod:") for n in body["nodes"] if n["entity_type"] == "lod")
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

    # Clamped depth=99 -> 4 and max_nodes=4 triggers truncated=True
    res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={work_id}&depth=99&max_nodes=4")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["meta"]["depth"] == 4
    assert len(data["nodes"]) == 4
    assert data["meta"]["truncated"] is True
    assert data["meta"]["truncated_reason"] in ("node_cap", "both")

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


def test_catalog_graph_encodes_contributor_urls(client, app):
    """Contributor node URLs encode '&' and '+' so /collection?q=... stays intact."""
    with app.app_context():
        w = Work(title="Encoded Contributor Work")
        db.session.add(w)
        db.session.flush()
        c = Contributor(name="Simon & Schuster + Co", type="organization")
        db.session.add(c)
        db.session.flush()
        db.session.add(WorkContribution(work_id=w.id, contributor_id=c.id, role="publisher", sequence=0))
        db.session.commit()
        wid = w.id

    res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={wid}&depth=1&edge_types=contributors")
    assert res.status_code == 200
    contrib_nodes = [n for n in res.get_json()["data"]["nodes"] if n["entity_type"] == "contributor"]
    assert len(contrib_nodes) == 1
    assert contrib_nodes[0]["url"] == "/collection?q=Simon+%26+Schuster+%2B+Co"


def test_catalog_graph_depth_4_and_max_edges_cap(client, app):
    """Depth 3..4 traverses multi-hop FRBR chains and enforces max_edges truncation metadata."""
    with app.app_context():
        u = User(email="g4-owner@example.com", display_name="G4 Owner", is_active=True)
        u.set_password("StrongPass123!")
        db.session.add(u)
        db.session.flush()
        w = Work(title="Depth 4 Root")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, format="hardcover", meta={"title": "Depth 4 Ed"})
        db.session.add(m)
        db.session.flush()
        db.session.add(Item(manifestation_id=m.id, owner_id=u.id, visibility="public", is_hidden=False))
        db.session.commit()
        w_id = w.id

    res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={w_id}&depth=4&max_edges=2")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["meta"]["depth"] == 4
    assert data["meta"]["max_edges"] == 2
    assert len(data["edges"]) <= 2
    assert data["meta"]["truncated"] is True
    assert data["meta"]["truncated_reason"] in ("edge_cap", "both")


def test_catalog_graph_library_mode_and_federation_consent(client, app):
    """Library mode returns anchor=None, honors entity_types, and excludes non-consented public items."""
    from app.db.federation import FederationConsent

    with app.app_context():
        consented = User(email="consented@example.com", display_name="Consented", is_active=True)
        consented.set_password("StrongPass123!")
        opted_out = User(email="optedout@example.com", display_name="OptedOut", is_active=True)
        opted_out.set_password("StrongPass123!")
        db.session.add_all([consented, opted_out])
        db.session.flush()
        db.session.add(FederationConsent(user_id=opted_out.id, federated_collection=False))

        w = Work(title="Library Explorer Work")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, format="paperback", meta={"title": "Library Ed"})
        db.session.add(m)
        db.session.flush()
        it_ok = Item(manifestation_id=m.id, owner_id=consented.id, visibility="public", is_hidden=False)
        it_no = Item(manifestation_id=m.id, owner_id=opted_out.id, visibility="public", is_hidden=False)
        db.session.add_all([it_ok, it_no])
        db.session.commit()
        ok_id, no_id = it_ok.id, it_no.id

    res = client.get("/api/catalog/graph?mode=library&entity_types=work,item")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["anchor"] is None
    assert data["mode"] == "library"
    node_ids = {n["id"] for n in data["nodes"]}
    assert f"item:{ok_id}" in node_ids
    assert f"item:{no_id}" not in node_ids
    assert all(n["entity_type"] in ("work", "item") for n in data["nodes"])


def test_catalog_graph_person_contributor_and_organization_roots(app, client):
    """Verify person, contributor, and organization roots + Work/Expression/Manifestation/LOD + depth=2."""
    from app.db.models import ExpressionContribution, ManifestationContribution

    with app.app_context():
        person = Contributor(name="Stanisław Lem", type="person")
        org = Contributor(name="Wydawnictwo Literackie", type="organization")
        db.session.add_all([person, org])
        db.session.flush()

        w1 = Work(title="Solaris")
        w2 = Work(title="Cyberiada")
        db.session.add_all([w1, w2])
        db.session.flush()

        e1 = Expression(work_id=w1.id, content_type="text", language="pl")
        db.session.add(e1)
        db.session.flush()

        m1 = Manifestation(expression_id=e1.id, format="hardcover", meta={"title": "Solaris Wyd. 1"})
        db.session.add(m1)
        db.session.flush()

        db.session.add(WorkContribution(work_id=w1.id, contributor_id=person.id, role="author", sequence=1))
        db.session.add(WorkContribution(work_id=w2.id, contributor_id=person.id, role="author", sequence=1))
        db.session.add(ExpressionContribution(expression_id=e1.id, contributor_id=person.id, role="translator", sequence=1))
        db.session.add(ManifestationContribution(manifestation_id=m1.id, contributor_id=org.id, role="publisher", sequence=1))

        accepted_lod = SemanticLink(
            entity_type="contributor",
            entity_id=person.id,
            authority="wikidata",
            external_uri="https://www.wikidata.org/wiki/Q230741",
            pref_label="Stanisław Lem",
            status="accepted",
        )
        pending_lod = SemanticLink(
            entity_type="contributor",
            entity_id=person.id,
            authority="viaf",
            external_uri="https://viaf.org/viaf/56612733",
            pref_label="Pending Lem",
            status="pending",
        )
        db.session.add_all([accepted_lod, pending_lod])
        db.session.commit()
        person_id, org_id, w1_id, w2_id, e1_id, m1_id = person.id, org.id, w1.id, w2.id, e1.id, m1.id

    # 1. Anchor on person alias -> resolves to contributor:<id>
    res = client.get(f"/api/catalog/graph?entity_type=person&entity_id={person_id}&depth=1")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["anchor"]["node_id"] == f"contributor:{person_id}"
    nodes_by_id = {n["id"]: n for n in data["nodes"]}
    assert nodes_by_id[f"contributor:{person_id}"]["contributor_type"] == "person"
    assert nodes_by_id[f"contributor:{person_id}"]["is_anchor"] is True
    assert f"work:{w1_id}" in nodes_by_id
    assert f"work:{w2_id}" in nodes_by_id
    assert f"expression:{e1_id}" in nodes_by_id
    person_lod_uris = {n.get("external_uri") for n in data["nodes"] if n["entity_type"] == "lod"}
    assert "https://www.wikidata.org/wiki/Q230741" in person_lod_uris
    assert "https://viaf.org/viaf/56612733" not in person_lod_uris

    # 2. Organization contributor root
    org_res = client.get(f"/api/catalog/graph?entity_type=contributor&entity_id={org_id}&depth=1")
    assert org_res.status_code == 200
    org_data = org_res.get_json()["data"]
    org_nodes = {n["id"]: n for n in org_data["nodes"]}
    assert org_nodes[f"contributor:{org_id}"]["contributor_type"] == "organization"
    assert f"manifestation:{m1_id}" in org_nodes

    # 3. Depth=2 from Work A traverses through Contributor to sibling Work B
    w_res = client.get(f"/api/catalog/graph?entity_type=work&entity_id={w1_id}&depth=2")
    assert w_res.status_code == 200
    w_nodes = {n["id"]: n for n in w_res.get_json()["data"]["nodes"]}
    assert f"contributor:{person_id}" in w_nodes
    assert f"work:{w2_id}" in w_nodes


def test_catalog_graph_series_roots_and_non_series_404(app, client):
    """Verify series roots resolve to work:<id> for explicit and legacy series, and 404 on plain works."""
    with app.app_context():
        explicit_series = Work(title="Dune Chronicles", work_kind="series")
        legacy_series = Work(title="Legacy Series Container", work_kind=None)
        plain_work = Work(title="Standalone Book", work_kind="monograph")
        member_work = Work(title="Dune")
        db.session.add_all([explicit_series, legacy_series, plain_work, member_work])
        db.session.flush()
        db.session.add(WorkSeriesMembership(series_work_id=explicit_series.id, work_id=member_work.id, sequence=1))
        db.session.add(WorkSeriesMembership(series_work_id=legacy_series.id, work_id=member_work.id, sequence=2))
        db.session.commit()
        exp_id, leg_id, plain_id, mem_id = explicit_series.id, legacy_series.id, plain_work.id, member_work.id

    res1 = client.get(f"/api/catalog/graph?entity_type=series&entity_id={exp_id}&depth=1")
    assert res1.status_code == 200
    d1 = res1.get_json()["data"]
    assert d1["anchor"]["node_id"] == f"work:{exp_id}"
    assert any(n["id"] == f"work:{mem_id}" for n in d1["nodes"])

    res2 = client.get(f"/api/catalog/graph?entity_type=series&entity_id={leg_id}&depth=1")
    assert res2.status_code == 200
    assert res2.get_json()["data"]["anchor"]["node_id"] == f"work:{leg_id}"

    res404 = client.get(f"/api/catalog/graph?entity_type=series&entity_id={plain_id}&depth=1")
    assert res404.status_code == 404


def test_catalog_graph_search_diacritics_visibility_limits_and_federation_head(app, client):
    """Verify /api/catalog/graph/search diacritic folding, 3-tier Item visibility, limits, 400s, and federation mode."""
    with app.app_context():
        owner = User(email="search_owner@iqoqo.local", public_username="s_owner", visibility="public")
        friend = User(email="search_friend@iqoqo.local", public_username="s_friend", visibility="public")
        stranger = User(email="search_stranger@iqoqo.local", public_username="s_stranger", visibility="public")
        db.session.add_all([owner, friend, stranger])
        db.session.flush()
        db.session.add(UserFriendship(requester_id=owner.id, addressee_id=friend.id, status="accepted"))

        lem = Contributor(name="Stanisław Lem", type="person")
        series_w = Work(title="Stanisław Lem Dzieła Zebrane", work_kind="series")
        secret_w = Work(title="SecretChronicleCopy")
        db.session.add_all([lem, series_w, secret_w])
        db.session.flush()
        expr = Expression(work_id=secret_w.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        man = Manifestation(expression_id=expr.id, format="paperback", meta={"title": "SecretChronicleCopy"})
        db.session.add(man)
        db.session.flush()

        it_pub = Item(manifestation_id=man.id, owner_id=owner.id, visibility="public", is_hidden=False)
        it_fri = Item(manifestation_id=man.id, owner_id=owner.id, visibility="friends_only", is_hidden=False)
        it_pri = Item(manifestation_id=man.id, owner_id=owner.id, visibility="private", is_hidden=True)
        db.session.add_all([it_pub, it_fri, it_pri])
        db.session.commit()
        pub_id, fri_id, pri_id = it_pub.id, it_fri.id, it_pri.id
        owner_hdr = _auth_header(owner)
        friend_hdr = _auth_header(friend)
        stranger_hdr = _auth_header(stranger)

    # 1. Diacritic-insensitive search across person + series
    res = client.get("/api/catalog/graph/search?q=Stanislaw&types=person,series")
    assert res.status_code == 200
    rows = res.get_json()["data"]
    assert any(r["entity_type"] == "person" and r["label"] == "Stanisław Lem" for r in rows)
    assert any(r["entity_type"] == "series" and r["label"] == "Stanisław Lem Dzieła Zebrane" for r in rows)

    # 2. Three-tier Item visibility in SQL
    anon_items = client.get("/api/catalog/graph/search?q=SecretChronicleCopy&types=item").get_json()["data"]
    assert {r["entity_id"] for r in anon_items} == {pub_id}

    stranger_items = client.get("/api/catalog/graph/search?q=SecretChronicleCopy&types=item", headers=stranger_hdr).get_json()["data"]
    assert {r["entity_id"] for r in stranger_items} == {pub_id}

    friend_items = client.get("/api/catalog/graph/search?q=SecretChronicleCopy&types=item", headers=friend_hdr).get_json()["data"]
    assert {r["entity_id"] for r in friend_items} == {pub_id, fri_id}

    owner_items = client.get("/api/catalog/graph/search?q=SecretChronicleCopy&types=item", headers=owner_hdr).get_json()["data"]
    assert {r["entity_id"] for r in owner_items} == {pub_id, fri_id, pri_id}

    # 3. Blank query, limit clamping, invalid types, and FEDERATION_HEAD_MODE=true
    assert client.get("/api/catalog/graph/search?q=%20%20").get_json()["data"] == []
    assert client.get("/api/catalog/graph/search?q=Lem&types=invalid_type").status_code == 400

    app.config["FEDERATION_HEAD_MODE"] = True
    try:
        fed_res = client.get("/api/catalog/graph/search?q=Lem&limit=500")
        assert fed_res.status_code == 200
    finally:
        app.config["FEDERATION_HEAD_MODE"] = False


def test_catalog_graph_person_deduplicates_lod_nodes_by_canonical_uri(app, client):
    """Person graphs collapse duplicate/shared author LOD SemanticLinks into one canonical LOD node."""
    with app.app_context():
        king = Contributor(name="Stephen King", type="person")
        db.session.add(king)
        db.session.flush()

        w_it = Work(title="It")
        w_shining = Work(title="The Shining")
        db.session.add_all([w_it, w_shining])
        db.session.flush()

        db.session.add(WorkContribution(work_id=w_it.id, contributor_id=king.id, role="author", sequence=0))
        db.session.add(WorkContribution(work_id=w_shining.id, contributor_id=king.id, role="author", sequence=0))

        # Multiple SemanticLink rows referencing the same canonical external URI across http/https/trailing-slash
        # plus Work-attached author LOD rows from DBpedia reconciliation.
        db.session.add_all(
            [
                SemanticLink(
                    entity_type="contributor",
                    entity_id=king.id,
                    authority="dbpedia",
                    external_uri="http://dbpedia.org/resource/Stephen_King",
                    pref_label="",
                    status="accepted",
                ),
                SemanticLink(
                    entity_type="contributor",
                    entity_id=king.id,
                    authority="dbpedia",
                    external_uri="https://dbpedia.org/resource/Stephen_King/",
                    pref_label="Stephen King",
                    status="accepted",
                ),
                SemanticLink(
                    entity_type="work",
                    entity_id=w_it.id,
                    authority="dbpedia",
                    external_uri="https://DBpedia.org/resource/Stephen_King",
                    pref_label="Stephen King",
                    status="accepted",
                ),
                SemanticLink(
                    entity_type="work",
                    entity_id=w_shining.id,
                    authority="dbpedia",
                    external_uri="http://dbpedia.org/resource/Stephen_King/",
                    pref_label="Stephen King",
                    status="accepted",
                ),
            ]
        )
        db.session.commit()
        king_id, it_id, shining_id = king.id, w_it.id, w_shining.id

    # 1. Bounded person graph (depth=2) must emit exactly ONE canonical LOD node for Stephen King
    res = client.get(f"/api/catalog/graph?entity_type=person&entity_id={king_id}&depth=2")
    assert res.status_code == 200
    data = res.get_json()["data"]
    lod_nodes = [n for n in data["nodes"] if n["entity_type"] == "lod"]
    assert len(lod_nodes) == 1
    assert lod_nodes[0]["label"] == "Stephen King"
    assert lod_nodes[0]["canonical_uri"] == "https://dbpedia.org/resource/Stephen_King"

    lod_id = lod_nodes[0]["id"]
    same_as_edges = [e for e in data["edges"] if e["relation"] == "same_as" and e["target"] == lod_id]
    # One deduplicated same_as edge per unique source entity (contributor + both works = 3)
    assert {(e["source"], e["target"]) for e in same_as_edges} == {
        (f"contributor:{king_id}", lod_id),
        (f"work:{it_id}", lod_id),
        (f"work:{shining_id}", lod_id),
    }
    assert len(same_as_edges) == 3

    # 2. Full-library mode anchors contributor LOD links too and deduplicates to 1 node
    lib_res = client.get("/api/catalog/graph?mode=library&entity_types=work,contributor,lod&edge_types=contributors,lod")
    assert lib_res.status_code == 200
    lib_data = lib_res.get_json()["data"]
    lib_king_lods = [
        n for n in lib_data["nodes"] if n["entity_type"] == "lod" and n.get("canonical_uri") == "https://dbpedia.org/resource/Stephen_King"
    ]
    assert len(lib_king_lods) == 1
    assert any(
        e["source"] == f"contributor:{king_id}" and e["target"] == lib_king_lods[0]["id"] and e["relation"] == "same_as"
        for e in lib_data["edges"]
    )
