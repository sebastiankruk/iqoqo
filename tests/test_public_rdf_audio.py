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
"""Tests for C118 audio pressing RDF triples and AI-fetchable shared collection feeds."""

from __future__ import annotations

import json
import uuid

import pytest
from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF

from app.core.frbr_service import IQOQO, SCHEMA, build_collection_rdf_graph
from app.db import db
from app.db.auth import User
from app.db.core import Expression, Item, Manifestation, Work
from app.db.social import SharedCollection


def _seed_audio_share(count: int = 2, include_hidden: bool = False) -> str:
    """Create a user, audio items, and a shared collection returning its share token."""
    user = User(
        email=f"audio_{uuid.uuid4().hex[:8]}@iqoqo.local", public_username=f"audiophile_{uuid.uuid4().hex[:6]}", visibility="public"
    )
    db.session.add(user)
    db.session.flush()

    work = Work(title="Kind of Blue", meta={"authors": ["Miles Davis"]})
    db.session.add(work)
    db.session.flush()

    expr = Expression(work_id=work.id, content_type="music", kind="studio_recording", language="en")
    db.session.add(expr)
    db.session.flush()

    for idx in range(count):
        manifestation = Manifestation(
            expression_id=expr.id,
            format="vinyl",
            publisher="Columbia",
            ean=f"007464649351{idx}",
            meta={
                "title": f"Kind of Blue Pressing #{idx + 1}",
                "format": "vinyl",
                "record_label": "Columbia",
                "catalog_number": f"CL-1355-{idx + 1}",
                "ean": "0074646493519",
                "release_year": "1959",
                "country": "US",
                "matrix_runout": f"XLP-47324-{idx + 1}",
                "lod_links": {"discogs_uri": f"https://www.discogs.com/release/{1000 + idx}"},
            },
        )
        db.session.add(manifestation)
        db.session.flush()

        item = Item(
            manifestation_id=manifestation.id,
            owner_id=user.id,
            status="read",
            collection_status="available",
            is_hidden=False,
            visibility="public",
        )
        db.session.add(item)

    if include_hidden:
        hidden_m = Manifestation(
            expression_id=expr.id,
            format="cd",
            publisher="Hidden Label",
            meta={"title": "Secret Pressing", "format": "cd", "catalog_number": "HIDDEN-01"},
        )
        db.session.add(hidden_m)
        db.session.flush()
        hidden_item = Item(
            manifestation_id=hidden_m.id,
            owner_id=user.id,
            status="read",
            collection_status="available",
            is_hidden=True,
        )
        db.session.add(hidden_item)
        private_item = Item(
            manifestation_id=hidden_m.id,
            owner_id=user.id,
            status="read",
            collection_status="available",
        )
        private_item.set_visibility("private")
        db.session.add(private_item)

    token = f"share-audio-{uuid.uuid4().hex[:12]}"
    share = SharedCollection(user_id=user.id, name="HiFi Vinyl", share_token=token, filters={})
    db.session.add(share)
    db.session.commit()
    return token


def test_build_collection_rdf_graph_emits_audio_pressing_triples() -> None:
    """Verify _emit_audio_rdf_triples emits MusicAlbum/MusicRelease and omits absent fields."""
    items = [
        {
            "id": 1,
            "manifestation_id": 10,
            "title": "Kind of Blue",
            "content_type": "music",
            "format": "vinyl",
            "publisher": "Columbia",
            "catalog_number": "CL 1355",
            "ean": "0074646493519",
            "publication_year": "1959",
            "country": "US",
            "matrix_runout": "XLP-47324-1A",
            "lod_links": {"discogs_uri": "https://www.discogs.com/release/12345"},
        },
        {
            "id": 2,
            "manifestation_id": 11,
            "title": "Minimal Audio",
            "content_type": "music",
            "format": "cd",
        },
    ]
    g = build_collection_rdf_graph(items, "https://iqoqo.cc")

    m1 = next(g.subjects(SCHEMA.catalogNumber, Literal("CL 1355")))
    assert (m1, RDF.type, SCHEMA.MusicAlbum) in g
    assert (m1, RDF.type, SCHEMA.MusicRelease) in g
    assert (m1, SCHEMA.musicReleaseFormat, Literal("vinyl")) in g
    assert (m1, SCHEMA.recordLabel, Literal("Columbia")) in g
    assert (m1, SCHEMA.gtin13, Literal("0074646493519")) in g
    assert (m1, SCHEMA.countryOfOrigin, Literal("US")) in g
    assert (m1, IQOQO.matrixRunout, Literal("XLP-47324-1A")) in g
    assert any(str(o) == "https://www.discogs.com/release/12345" for o in g.objects(m1, OWL.sameAs))

    # Minimal audio manifestation must omit catalogNumber when absent
    m2 = next(g.subjects(SCHEMA.name, Literal("Minimal Audio")))
    assert (m2, RDF.type, SCHEMA.MusicAlbum) in g
    assert list(g.objects(m2, SCHEMA.catalogNumber)) == []


@pytest.mark.usefixtures("app")
def test_shared_collection_json_and_rdf_negotiation(client, app) -> None:
    """Verify enriched JSON payload, ?format=jsonld|turtle, hidden exclusion, and 400 on bad format."""
    with app.app_context():
        token = _seed_audio_share(count=3, include_hidden=True)

    # 1. Enriched JSON payload excludes hidden/private items and exposes pressing fields
    res_json = client.get(f"/api/public/share/{token}?limit=1000")
    assert res_json.status_code == 200
    payload = res_json.get_json()
    assert payload["success"] is True
    items = payload["data"]["items"]
    assert len(items) == 3
    assert all(it["title"] != "Secret Pressing" for it in items)
    first = items[0]
    assert first["content_type"] == "music"
    assert first["format"] == "vinyl"
    assert first["publisher"] == "Columbia"
    assert first["ean"] == "0074646493519"
    assert first["country"] == "US"
    assert first["catalog_number"].startswith("CL-1355-")

    # 2. ?format=jsonld&limit=1000 without custom Accept headers
    res_jsonld = client.get(f"/api/public/share/{token}?format=jsonld&limit=1000")
    assert res_jsonld.status_code == 200
    assert "application/ld+json" in res_jsonld.headers.get("Content-Type", "")
    parsed_jsonld = json.loads(res_jsonld.data.decode("utf-8"))
    assert parsed_jsonld

    # 3. ?format=turtle on /api/public/rdf/share/<token>
    res_ttl = client.get(f"/api/public/rdf/share/{token}?format=turtle&limit=999999")
    assert res_ttl.status_code == 200
    assert "text/turtle" in res_ttl.headers.get("Content-Type", "")
    g = Graph()
    g.parse(data=res_ttl.data.decode("utf-8"), format="turtle")
    assert len(list(g.subjects(SCHEMA.musicReleaseFormat, Literal("vinyl")))) == 3
    assert len(list(g.subjects(SCHEMA.catalogNumber, Literal("HIDDEN-01")))) == 0

    # 4. Unknown format rejected with JSON 400
    res_bad = client.get(f"/api/public/share/{token}?format=unknown-fmt")
    assert res_bad.status_code == 400
    assert res_bad.get_json()["code"] == 400

    res_bad_rdf = client.get(f"/api/public/rdf/share/{token}?format=unknown-fmt")
    assert res_bad_rdf.status_code == 400
    assert res_bad_rdf.get_json()["code"] == 400


@pytest.mark.usefixtures("app")
def test_shared_collection_sql_pagination_and_accept_jsonld(client, app) -> None:
    """Verify SQL page/per_page pagination and Accept: application/ld+json | application/json+ld."""
    with app.app_context():
        token = _seed_audio_share(count=5, include_hidden=True)

    page1 = client.get(f"/api/public/share/{token}?page=1&per_page=2")
    assert page1.status_code == 200
    d1 = page1.get_json()["data"]
    assert d1["total"] == 5
    assert d1["page"] == 1
    assert d1["per_page"] == 2
    assert d1["pages"] == 3
    assert len(d1["items"]) == 2

    page3 = client.get(f"/api/public/share/{token}?page=3&per_page=2")
    assert page3.status_code == 200
    d3 = page3.get_json()["data"]
    assert d3["page"] == 3
    assert len(d3["items"]) == 1

    for accept_hdr in ("application/ld+json", "application/json+ld"):
        res_ld = client.get(f"/api/public/share/{token}?page=1&per_page=2", headers={"Accept": accept_hdr})
        assert res_ld.status_code == 200
        assert "application/ld+json" in res_ld.headers.get("Content-Type", "")
        assert res_ld.headers.get("Cache-Control") == "public, max-age=300"
        parsed = json.loads(res_ld.data.decode("utf-8"))
        assert parsed


@pytest.mark.usefixtures("app")
def test_shared_wishlist_paginates_intents_and_includes_want_to_build(client, app) -> None:
    """Shared wishlist collections include want_to_build intents and slice results by page/per_page (L-04)."""
    from app.db.models import UserWorkIntent

    with app.app_context():
        user = User(
            email=f"wish_{uuid.uuid4().hex[:8]}@iqoqo.local",
            public_username=f"wishuser_{uuid.uuid4().hex[:6]}",
            visibility="public",
        )
        db.session.add(user)
        db.session.flush()

        for idx, (content_type, status) in enumerate(
            [("lego", "want_to_build"), ("text", "want_to_read"), ("music", "want_to_listen")], start=1
        ):
            w = Work(title=f"Wishlist Work {idx}", meta={"authors": ["Builder"]})
            db.session.add(w)
            db.session.flush()
            e = Expression(work_id=w.id, content_type=content_type, language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id, format="standard_set" if content_type == "lego" else "book", meta={})
            db.session.add(m)
            db.session.flush()
            db.session.add(
                UserWorkIntent(
                    user_id=user.id,
                    work_id=w.id,
                    expression_id=e.id,
                    manifestation_id=m.id,
                    status=status,
                    is_hidden=False,
                )
            )

        token = f"share-wish-{uuid.uuid4().hex[:12]}"
        db.session.add(SharedCollection(user_id=user.id, name="Wishlist Share", share_token=token, filters={"status": "wish_list"}))
        db.session.commit()

    page1 = client.get(f"/api/public/share/{token}?page=1&per_page=2").get_json()["data"]
    assert page1["total"] == 3
    assert page1["pages"] == 2
    assert len(page1["items"]) == 2

    page2 = client.get(f"/api/public/share/{token}?page=2&per_page=2").get_json()["data"]
    assert len(page2["items"]) == 1

    all_statuses = {item["status"] for item in page1["items"] + page2["items"]}
    assert "want_to_build" in all_statuses


@pytest.mark.usefixtures("app")
def test_fetch_shared_collection_by_token_pg_search_offset(app, monkeypatch) -> None:
    """fetch_shared_collection_by_token passes offset to SearchService without double-offsetting (L-02)."""
    from app.api.public_items import fetch_shared_collection_by_token
    from app.core.search_service import SearchService

    with app.app_context():
        user = User(
            email=f"pg_{uuid.uuid4().hex[:8]}@iqoqo.local",
            public_username=f"pguser_{uuid.uuid4().hex[:6]}",
            visibility="public",
        )
        db.session.add(user)
        db.session.flush()
        work = Work(title="PG Search Item", meta={"authors": ["Author"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        man = Manifestation(expression_id=expr.id, format="book", meta={})
        db.session.add(man)
        db.session.flush()
        item = Item(
            manifestation_id=man.id, owner_id=user.id, status="read", collection_status="available", is_hidden=False, visibility="public"
        )
        db.session.add(item)
        db.session.flush()
        token = f"share-pg-{uuid.uuid4().hex[:12]}"
        db.session.add(SharedCollection(user_id=user.id, name="PG Search", share_token=token, filters={"query": "PG"}))
        db.session.commit()

        captured_calls: list[dict[str, object]] = []

        def _fake_search(q, user_id, limit, offset, **kwargs):
            captured_calls.append({"limit": limit, "offset": offset})
            return 2, [{"item_id": item.id}]

        monkeypatch.setattr(SearchService, "search_items", staticmethod(_fake_search))
        monkeypatch.setattr(db.engine.dialect, "name", "postgresql")
        results = fetch_shared_collection_by_token(token=token, limit=1, offset=1)

        assert captured_calls == [{"limit": 1, "offset": 1}]
        assert [r.id for r in results] == [item.id]


def test_dvd_with_catalog_number_never_emits_music_album():
    """C141: A movie DVD with catalog_number and drifted content_type='music' must not emit MusicAlbum/MusicRelease."""
    from rdflib import RDF, Graph, URIRef

    from app.core.frbr_service import SCHEMA, _emit_audio_rdf_triples

    g = Graph()
    m_uri = URIRef("https://iqoqo.cc/manifestation/999")
    _emit_audio_rdf_triples(
        g,
        m_uri,
        None,
        {"format": "dvd", "catalog_number": "CAT-999"},
        content_type="music",
    )
    assert (m_uri, RDF.type, SCHEMA.MusicAlbum) not in g
    assert (m_uri, RDF.type, SCHEMA.MusicRelease) not in g
