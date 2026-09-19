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
"""Comprehensive test suite for enhanced RDF serialization and LOD endpoints.

Validates:
- Granular Schema.org type mappings (Book, Audiobook, MusicAlbum, Movie, Game, Product, MusicEvent)
- Relational and provenance enrichment (publisher, inLanguage, datePublished, contributor, image, prov:wasDerivedFrom, isPartOf, hasPart, Collection)
- Domain mappings for Concerts and Board Games
- Multi-format serialization (Turtle, JSON-LD, N-Triples)
- Generator-based streaming chunk generation (stream_collection_to_rdf)
- Eager loading query optimization (MOD-FRBR-02) and fallback hydration
- HTTP content negotiation and streaming in public API endpoints
"""

import json

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.frbr_service import (
    FRBR,
    PROV,
    SCHEMA,
    SCHEMA_TYPE_MAP,
    SIOC,
    _eager_load_items_fallback,
    _enrich_graph_from_db,
    build_collection_rdf_graph,
    serialize_collection_to_rdf,
    stream_collection_to_rdf,
)
from app.db.audio import ExpressionContribution, WorkContribution, WorkPart
from app.db.contributions import Contributor, ManifestationContribution
from app.db.core import (
    ImageScan,
    UserCollectionItem,
)
from app.db.models import Expression, Item, Manifestation, SharedCollection, User, Work, db


class TestSchemaOrgTypeMapping:
    """Test mapping of FRBR content_type to Schema.org classes."""

    def test_schema_type_map_entries(self):
        assert SCHEMA_TYPE_MAP["text"] == SCHEMA.Book
        assert SCHEMA_TYPE_MAP["audiobook"] == SCHEMA.Audiobook
        assert SCHEMA_TYPE_MAP["music"] == SCHEMA.MusicAlbum
        assert SCHEMA_TYPE_MAP["movie"] == SCHEMA.Movie
        assert SCHEMA_TYPE_MAP["board_game"] == SCHEMA.Game
        assert SCHEMA_TYPE_MAP["puzzle"] == SCHEMA.Product
        assert SCHEMA_TYPE_MAP["concert"] == SCHEMA.MusicEvent

    def test_serialization_asserts_both_frbr_and_schema_types(self):
        items = [
            {
                "id": "item1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Dune",
                "content_type": "text",
            }
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")
        m_uri = URIRef("http://testserver/api/public/manifestations/m1")

        assert (m_uri, RDF.type, FRBR.Manifestation) in g
        assert (m_uri, RDF.type, SCHEMA.CreativeWork) in g
        assert (m_uri, RDF.type, SCHEMA.Book) in g


class TestRelationalAndProvenanceEnrichment:
    """Test relational, structural, and provenance RDF triple generation."""

    def test_enrichment_publisher_language_date_image(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Solaris",
                "publisher": "Wydawnictwo Literackie",
                "language": "pl",
                "publication_date": "1961-05-01",
                "cover_url": "https://covers.example.com/solaris.jpg",
            }
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")
        m_uri = URIRef("http://testserver/api/public/manifestations/m1")

        assert (m_uri, SCHEMA.publisher, Literal("Wydawnictwo Literackie")) in g
        assert (m_uri, SCHEMA.inLanguage, Literal("pl")) in g
        assert (m_uri, SCHEMA.datePublished, Literal("1961-05-01")) in g
        assert (m_uri, SCHEMA.image, URIRef("https://covers.example.com/solaris.jpg")) in g

    def test_contributors_enrichment(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Illustrated Work",
                "contributors": [
                    {"id": "c1", "name": "Stanislaw Lem", "type": "person"},
                    {"id": "c2", "name": "Illustrator Studio", "type": "organization"},
                ],
            }
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")

        m_uri = URIRef("http://testserver/api/public/manifestations/m1")
        c1_uri = URIRef("http://testserver/api/public/contributors/c1")
        c2_uri = URIRef("http://testserver/api/public/contributors/c2")

        assert (c1_uri, RDF.type, SCHEMA.Person) in g
        assert (c1_uri, SCHEMA.name, Literal("Stanislaw Lem")) in g
        assert (c2_uri, RDF.type, SCHEMA.Organization) in g
        assert (c2_uri, SCHEMA.name, Literal("Illustrator Studio")) in g
        assert (m_uri, SCHEMA.contributor, c1_uri) in g
        assert (m_uri, SCHEMA.contributor, c2_uri) in g

    def test_provenance_links(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Open Library Book",
                "source": "openlibrary",
                "openlibrary_id": "OL123M",
            },
            {
                "id": "i2",
                "manifestation_id": "m2",
                "expression_id": "e2",
                "work_id": "w2",
                "title": "MusicBrainz Album",
                "source": "musicbrainz",
                "mbid": "mb-456",
            },
            {
                "id": "i3",
                "manifestation_id": "m3",
                "expression_id": "e3",
                "work_id": "w3",
                "title": "BGG Game",
                "source": "boardgamegeek",
                "bgg_id": "789",
            },
            {
                "id": "i4",
                "manifestation_id": "m4",
                "expression_id": "e4",
                "work_id": "w4",
                "title": "Direct URL",
                "source_url": "https://allegro.pl/oferta/1000",
            },
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")

        m1 = URIRef("http://testserver/api/public/manifestations/m1")
        m2 = URIRef("http://testserver/api/public/manifestations/m2")
        m3 = URIRef("http://testserver/api/public/manifestations/m3")
        m4 = URIRef("http://testserver/api/public/manifestations/m4")

        assert (m1, PROV.wasDerivedFrom, URIRef("https://openlibrary.org/books/OL123M")) in g
        assert (m2, PROV.wasDerivedFrom, URIRef("https://musicbrainz.org/release/mb-456")) in g
        assert (m3, PROV.wasDerivedFrom, URIRef("https://boardgamegeek.com/boardgame/789")) in g
        assert (m4, PROV.wasDerivedFrom, URIRef("https://allegro.pl/oferta/1000")) in g

    def test_part_whole_and_collection_root_nodes(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Child Volume",
                "is_part_of": "parent-boxset",
            }
        ]
        coll_uri = "http://testserver/u/testuser"
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle", collection_uri=coll_uri)
        g = Graph()
        g.parse(data=ttl, format="turtle")

        coll_node = URIRef(coll_uri)
        m_uri = URIRef("http://testserver/api/public/manifestations/m1")
        w_uri = URIRef("http://testserver/api/public/works/w1")
        parent_uri = URIRef("http://testserver/api/public/works/parent-boxset")

        # Collection root
        assert (coll_node, RDF.type, SCHEMA.Collection) in g
        assert (coll_node, SCHEMA.hasPart, m_uri) in g
        assert (m_uri, SCHEMA.isPartOf, coll_node) in g

        # Part-whole container
        assert (w_uri, SCHEMA.isPartOf, parent_uri) in g
        assert (parent_uri, SCHEMA.hasPart, w_uri) in g

    def test_enrich_graph_from_db_with_orm_models(self, app):
        with app.app_context():
            user = User(email="orm_enrich@iqoqo.local", display_name="Enrich User", public_username="enrichuser", visibility="public")
            db.session.add(user)
            db.session.flush()

            w = Work(title="Container Work")
            db.session.add(w)
            part_w = Work(title="Part Work")
            db.session.add(part_w)
            db.session.flush()

            wp = WorkPart(container_work_id=w.id, part_work_id=part_w.id)
            db.session.add(wp)

            contrib = Contributor(name="Famous Artist", type="person")
            db.session.add(contrib)
            db.session.flush()

            wc = WorkContribution(work_id=w.id, contributor_id=contrib.id, role="author")
            db.session.add(wc)

            e = Expression(work_id=w.id, content_type="text", language="en")
            db.session.add(e)
            db.session.flush()

            ec = ExpressionContribution(expression_id=e.id, contributor_id=contrib.id, role="editor")
            db.session.add(ec)

            m = Manifestation(expression_id=e.id, publisher="Famous Press")
            db.session.add(m)
            db.session.flush()

            mc = ManifestationContribution(manifestation_id=m.id, contributor_id=contrib.id, role="publisher")
            db.session.add(mc)

            it = Item(owner_id=user.id, manifestation_id=m.id, status="read")
            db.session.add(it)
            db.session.flush()

            scan = ImageScan(manifestation_id=m.id, file_path="scans/m_cover.jpg")
            db.session.add(scan)

            db.session.commit()

            ttl = serialize_collection_to_rdf([it], "http://testserver", output_format="turtle")
            g = Graph()
            g.parse(data=ttl, format="turtle")

            m_uri = URIRef(f"http://testserver/api/public/manifestations/{m.id}")
            w_uri = URIRef(f"http://testserver/api/public/works/{w.id}")
            part_uri = URIRef(f"http://testserver/api/public/works/{part_w.id}")
            c_uri = URIRef(f"http://testserver/api/public/contributors/{contrib.id}")
            img_uri = URIRef("http://testserver/scans/m_cover.jpg")

            assert (m_uri, SCHEMA.contributor, c_uri) in g
            assert (w_uri, SCHEMA.contributor, c_uri) in g
            assert (part_uri, SCHEMA.isPartOf, w_uri) in g
            assert (w_uri, SCHEMA.hasPart, part_uri) in g
            assert (m_uri, SCHEMA.image, img_uri) in g


class TestDomainSpecificMappings:
    """Test specialized domain mappings for Concerts and Board Games."""

    def test_concert_domain_mapping(self):
        items = [
            {
                "id": "c1",
                "manifestation_id": "mc1",
                "expression_id": "ec1",
                "work_id": "wc1",
                "title": "Live at Pompeii",
                "content_type": "concert",
                "performers": ["Pink Floyd"],
                "start_date": "1971-10-04",
                "location": "Pompeii Amphitheatre",
            }
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")
        m_uri = URIRef("http://testserver/api/public/manifestations/mc1")

        assert (m_uri, RDF.type, SCHEMA.MusicEvent) in g
        assert (m_uri, SCHEMA.performer, Literal("Pink Floyd")) in g
        assert (m_uri, SCHEMA.startDate, Literal("1971-10-04")) in g
        assert (m_uri, SCHEMA.location, Literal("Pompeii Amphitheatre")) in g

    def test_board_game_domain_mapping(self):
        items = [
            {
                "id": "g1",
                "manifestation_id": "mg1",
                "expression_id": "eg1",
                "work_id": "wg1",
                "title": "Catan",
                "content_type": "board_game",
                "min_players": 3,
                "max_players": 4,
            },
            {
                "id": "g2",
                "manifestation_id": "mg2",
                "expression_id": "eg2",
                "work_id": "wg2",
                "title": "Chess",
                "content_type": "board_game",
                "min_players": 2,
                "max_players": 2,
            },
        ]
        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")

        m1 = URIRef("http://testserver/api/public/manifestations/mg1")
        m2 = URIRef("http://testserver/api/public/manifestations/mg2")

        assert (m1, RDF.type, SCHEMA.Game) in g
        assert (m1, SCHEMA.numberOfPlayers, Literal("3-4")) in g
        assert (m2, RDF.type, SCHEMA.Game) in g
        assert (m2, SCHEMA.numberOfPlayers, Literal("2")) in g


class TestMultiFormatAndStreamingSerialization:
    """Test format conversion (Turtle, JSON-LD, N-Triples) and streaming generator."""

    @pytest.fixture
    def sample_items(self):
        return [
            {
                "id": f"item-{i}",
                "manifestation_id": f"mani-{i}",
                "expression_id": f"expr-{i}",
                "work_id": f"work-{i}",
                "title": f"Book {i}",
                "content_type": "text",
                "publisher": "Test Press",
            }
            for i in range(1, 11)
        ]

    def test_ntriples_serialization(self, sample_items):
        nt_payload = serialize_collection_to_rdf(sample_items, "http://testserver", output_format="nt")
        assert isinstance(nt_payload, str)
        assert len(nt_payload) > 0

        # Must parse as valid N-Triples
        g = Graph()
        g.parse(data=nt_payload, format="nt")
        assert len(g) > 0
        m1 = URIRef("http://testserver/api/public/manifestations/mani-1")
        assert (m1, RDF.type, SCHEMA.Book) in g

    def test_jsonld_serialization(self, sample_items):
        jsonld_payload = serialize_collection_to_rdf(sample_items, "http://testserver", output_format="json-ld")
        assert isinstance(jsonld_payload, str)
        # Parse JSON and parse RDF
        data = json.loads(jsonld_payload)
        assert "@graph" in data or "@context" in data

        g = Graph()
        g.parse(data=jsonld_payload, format="json-ld")
        assert len(g) > 0

    def test_turtle_serialization(self, sample_items):
        ttl_payload = serialize_collection_to_rdf(sample_items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl_payload, format="turtle")
        assert len(g) > 0

    def test_stream_collection_to_rdf_ntriples(self, sample_items):
        chunks = list(stream_collection_to_rdf(sample_items, "http://testserver", output_format="nt", chunk_size=3))
        # 10 items in chunks of 3 = 4 chunks
        assert len(chunks) == 4

        # Concatenated chunks must parse as valid N-Triples with all items
        combined_nt = "".join(chunks)
        g = Graph()
        g.parse(data=combined_nt, format="nt")
        for i in range(1, 11):
            m = URIRef(f"http://testserver/api/public/manifestations/mani-{i}")
            assert (m, RDF.type, SCHEMA.Book) in g

    def test_stream_collection_to_rdf_turtle(self, sample_items):
        chunks = list(stream_collection_to_rdf(sample_items, "http://testserver", output_format="turtle", chunk_size=5))
        assert len(chunks) == 2

        combined_ttl = "".join(chunks)
        g = Graph()
        g.parse(data=combined_ttl, format="turtle")
        assert len(g) > 0

    def test_stream_collection_to_rdf_jsonld(self, sample_items):
        chunks = list(stream_collection_to_rdf(sample_items, "http://testserver", output_format="json-ld", chunk_size=5))
        assert len(chunks) == 2
        for chunk in chunks:
            g = Graph()
            g.parse(data=chunk, format="json-ld")
            assert len(g) > 0


class TestQueryOptimizationAndFallback:
    """Test eager loading and elimination of N+1 queries (MOD-FRBR-02)."""

    def test_eager_load_items_fallback_hydrates_orm_instances(self, app):
        with app.app_context():
            user = User(
                email="eager_test@iqoqo.local",
                display_name="Eager Tester",
                public_username="eagertester",
                visibility="public",
            )
            db.session.add(user)
            db.session.flush()

            work = Work(title="Eager Book", meta={"authors": ["Eager Author"]})
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text", language="en")
            db.session.add(expr)
            db.session.flush()

            mani = Manifestation(expression_id=expr.id, isbn13="9781111111111", publisher="Eager House")
            db.session.add(mani)
            db.session.flush()

            item = Item(owner_id=user.id, manifestation_id=mani.id, status="read")
            db.session.add(item)
            db.session.commit()

            # Fetch bare Item without joinedload to simulate un-hydrated object
            bare_item = db.session.execute(select(Item).where(Item.id == item.id)).scalar_one()

            # Pass unhydrated instance into _eager_load_items_fallback
            hydrated_list = _eager_load_items_fallback([bare_item])
            assert len(hydrated_list) == 1
            h_item = hydrated_list[0]
            # Relations must be loaded
            assert h_item.manifestation is not None
            assert h_item.manifestation.expression is not None
            assert h_item.manifestation.expression.work is not None
            assert h_item.manifestation.title == "Eager Book"

            # Serialize and verify
            ttl = serialize_collection_to_rdf([bare_item], "http://testserver", output_format="turtle")
            g = Graph()
            g.parse(data=ttl, format="turtle")
            m_uri = URIRef(f"http://testserver/api/public/manifestations/{mani.id}")
            assert (m_uri, RDF.type, SCHEMA.Book) in g
            assert (m_uri, SCHEMA.publisher, Literal("Eager House")) in g

    def test_eager_loading_eliminates_n_plus_one_queries(self, app):
        from sqlalchemy import event

        from app.api.public import fetch_user_public_collection

        with app.app_context():
            user = User(
                email="nplus1_test@iqoqo.local",
                display_name="N+1 Tester",
                public_username="nplus1tester",
                visibility="public",
            )
            db.session.add(user)
            db.session.flush()

            # Create multiple items with full FRBR chain
            for i in range(5):
                w = Work(title=f"Work {i}", meta={"authors": [f"Author {i}"]})
                db.session.add(w)
                db.session.flush()

                e = Expression(work_id=w.id, content_type="text", language="en")
                db.session.add(e)
                db.session.flush()

                m = Manifestation(expression_id=e.id, isbn13=f"978333333333{i}", publisher=f"Press {i}")
                db.session.add(m)
                db.session.flush()

                it = Item(owner_id=user.id, manifestation_id=m.id, status="read", is_hidden=False)
                db.session.add(it)

            db.session.commit()

            # Measure query count during fetch AND hierarchy iteration
            # 1. Fetch collection items
            fetch_queries: list[str] = []

            def fetch_listener(conn, cursor, statement, parameters, context, executemany):
                fetch_queries.append(statement)

            event.listen(db.engine, "before_cursor_execute", fetch_listener)
            try:
                collection_items = fetch_user_public_collection("nplus1tester", limit=10)
            finally:
                event.remove(db.engine, "before_cursor_execute", fetch_listener)

            assert len(collection_items) == 5

            # 2. Traverse full FRBR hierarchy (Item -> Manifestation -> Expression -> Work)
            # Ensure ZERO queries are executed during traversal (all were eagerly loaded)
            traversal_queries: list[str] = []

            def traversal_listener(conn, cursor, statement, parameters, context, executemany):
                traversal_queries.append(statement)

            event.listen(db.engine, "before_cursor_execute", traversal_listener)
            try:
                for item in collection_items:
                    assert item.manifestation is not None
                    assert item.manifestation.expression is not None
                    assert item.manifestation.expression.work is not None
                    assert item.manifestation.expression.work.title.startswith("Work ")
            finally:
                event.remove(db.engine, "before_cursor_execute", traversal_listener)

            # Assert complete absence of N+1 lazy queries during iteration
            assert len(traversal_queries) == 0


class TestPublicApiEndpointsIntegration:
    """Test public API endpoints content negotiation and streaming responses."""

    @pytest.fixture
    def setup_public_catalog(self, app):
        with app.app_context():
            user = User(
                email="rdf_api_user@iqoqo.local",
                display_name="RDF API User",
                public_username="rdfuser",
                visibility="public",
            )
            db.session.add(user)
            db.session.flush()

            work = Work(title="Semantic Web Foundations", meta={"authors": ["Tim Berners-Lee"]})
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text", language="en")
            db.session.add(expr)
            db.session.flush()

            mani = Manifestation(expression_id=expr.id, isbn13="9782222222222", publisher="W3C Press")
            db.session.add(mani)
            db.session.flush()

            item = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False)
            db.session.add(item)

            shared_coll = SharedCollection(
                user_id=user.id,
                name="Public LOD Collection",
                share_token="test-rdf-token-123",
                filters={"tags": ["text"]},
            )
            db.session.add(shared_coll)
            db.session.commit()

            return {"username": user.public_username, "token": shared_coll.share_token}

    def test_public_user_items_ntriples_content_negotiation(self, client, setup_public_catalog):
        username = setup_public_catalog["username"]
        # Accept: application/n-triples
        res = client.get(f"/api/public/u/{username}/items", headers={"Accept": "application/n-triples"})
        assert res.status_code == 200
        assert "application/n-triples" in res.headers.get("Content-Type", "")

        g = Graph()
        g.parse(data=res.data.decode("utf-8"), format="nt")
        assert len(g) > 0
        books = list(g.subjects(RDF.type, SCHEMA.Book))
        assert len(books) >= 1

    def test_public_user_items_text_plain_content_negotiation(self, client, setup_public_catalog):
        username = setup_public_catalog["username"]
        # Accept: text/plain
        res = client.get(f"/api/public/u/{username}/items", headers={"Accept": "text/plain"})
        assert res.status_code == 200
        assert "application/n-triples" in res.headers.get("Content-Type", "")

        g = Graph()
        g.parse(data=res.data.decode("utf-8"), format="nt")
        assert len(g) > 0

    def test_public_user_items_streaming_response(self, client, setup_public_catalog):
        username = setup_public_catalog["username"]
        # Request stream=true with format=nt
        res = client.get(f"/api/public/u/{username}/items?stream=true&format=nt")
        assert res.status_code == 200
        assert "application/n-triples" in res.headers.get("Content-Type", "")

        g = Graph()
        g.parse(data=res.data.decode("utf-8"), format="nt")
        assert len(g) > 0

    def test_shared_collection_ntriples_and_streaming(self, client, setup_public_catalog):
        token = setup_public_catalog["token"]
        # Direct N-Triples negotiation
        res = client.get(f"/api/public/share/{token}", headers={"Accept": "application/n-triples"})
        assert res.status_code == 200
        assert "application/n-triples" in res.headers.get("Content-Type", "")

        g = Graph()
        g.parse(data=res.data.decode("utf-8"), format="nt")
        assert len(g) > 0

        # Streaming request
        stream_res = client.get(f"/api/public/share/{token}?stream=true&format=nt")
        assert stream_res.status_code == 200
        g_stream = Graph()
        g_stream.parse(data=stream_res.data.decode("utf-8"), format="nt")
        assert len(g_stream) > 0
