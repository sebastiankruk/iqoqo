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

"""Unit and integration tests for Cartographic Maps and Map Supplements (v1.0.1 - C105)."""

import io
import uuid
from unittest.mock import patch

import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from app.core.format_normalizer import normalize_format
from app.core.frbr_service import SCHEMA, serialize_collection_to_rdf
from app.core.meta_display import build_display_projection
from app.core.shacl_service import clear_cache, validate_graph
from app.core.taxonomy import MediaFormat
from app.db import db
from app.db.models import Expression, Item, Manifestation, User, Work

IQOQO = Namespace("https://iqoqo.org/ontology#")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")
FRBRER = Namespace("http://iflastandards.info/ns/frbr/frbrer/")


# ===========================================================================
# 1. Taxonomy & Format Normalization Tests
# ===========================================================================


class TestCartographicTaxonomy:
    """Validate cartographic formats and taxonomy normalization."""

    def test_cartographic_formats_present_in_taxonomy(self):
        assert MediaFormat.CARTOGRAPHIC_MAP == "cartographic_map"
        assert MediaFormat.ATLAS == "atlas"
        assert "cartographic_map" in MediaFormat.ALL
        assert "atlas" in MediaFormat.ALL

    def test_cartographic_format_normalization(self):
        assert normalize_format("map", content_type="text") == "cartographic_map"
        assert normalize_format("topographic_map", content_type="text") == "cartographic_map"
        assert normalize_format("folding_map", content_type="text") == "cartographic_map"
        assert normalize_format("road_map", content_type="text") == "cartographic_map"
        assert normalize_format("world_atlas", content_type="text") == "atlas"


# ===========================================================================
# 2. Map Attachments & Item map_insert_present API Tests
# ===========================================================================


@pytest.fixture
def sample_book_hierarchy(app):
    """Fixture providing a Work -> Expression -> Manifestation -> Item hierarchy."""
    with app.app_context():
        user = User.query.first()
        work = Work(title="The Lord of the Rings", meta={"authors": ["J.R.R. Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            format="book",
            meta={"title": "The Fellowship of the Ring"},
        )
        db.session.add(manif)
        db.session.flush()

        item = Item(
            manifestation_id=manif.id,
            owner_id=user.id,
            status="reading",
            collection_status="available",
            meta={},
        )
        db.session.add(item)
        db.session.commit()

        yield {
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
            "item_id": item.id,
            "user_id": str(user.id),
        }


class TestMapAttachmentsAPI:
    """Test REST API for map supplement attachments on Manifestation."""

    def test_add_map_attachment_json_and_get(self, client, app, normal_user_headers, sample_book_hierarchy):
        m_id = sample_book_hierarchy["manifestation_id"]

        # 1. Add map attachment via JSON
        res = client.post(
            f"/api/manifestations/{m_id}/map-attachments",
            json={
                "title": "Middle-earth Fold-out Map",
                "type": "fold_out_insert",
                "scale": "1:1000000",
                "projection": "Lambert Conformal Conic",
                "image_url": "https://example.com/me_map.jpg",
            },
            headers=normal_user_headers,
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["title"] == "Middle-earth Fold-out Map"
        assert data["type"] == "fold_out_insert"
        assert data["image_url"] == "https://example.com/me_map.jpg"
        att_id = data["id"]

        # 2. Get map attachments
        get_res = client.get(f"/api/manifestations/{m_id}/map-attachments")
        assert get_res.status_code == 200
        get_data = get_res.get_json()["data"]
        assert get_data["has_map"] is True
        assert get_data["map_scale"] == "1:1000000"
        assert get_data["map_projection"] == "Lambert Conformal Conic"
        assert len(get_data["attachments"]) == 1
        assert get_data["attachments"][0]["id"] == att_id

        # 3. Delete map attachment
        del_res = client.delete(
            f"/api/manifestations/{m_id}/map-attachments/{att_id}",
            headers=normal_user_headers,
        )
        assert del_res.status_code == 200

        # Verify list is empty and has_map is False
        get_after = client.get(f"/api/manifestations/{m_id}/map-attachments")
        get_after_data = get_after.get_json()["data"]
        assert get_after_data["has_map"] is False
        assert len(get_after_data["attachments"]) == 0

    def test_add_map_attachment_rejects_invalid_type(self, client, normal_user_headers, sample_book_hierarchy):
        m_id = sample_book_hierarchy["manifestation_id"]
        res = client.post(
            f"/api/manifestations/{m_id}/map-attachments",
            json={"title": "Invalid Map", "type": "not_a_valid_map_type"},
            headers=normal_user_headers,
        )
        assert res.status_code == 400
        assert "Invalid map type" in res.get_json()["error"]

    def test_delete_nonexistent_attachment_returns_404(self, client, normal_user_headers, sample_book_hierarchy):
        m_id = sample_book_hierarchy["manifestation_id"]
        res = client.delete(
            f"/api/manifestations/{m_id}/map-attachments/nonexistent-id",
            headers=normal_user_headers,
        )
        assert res.status_code == 404

    @patch("app.api.manifestations.save_upload_image", return_value="/static/gallery/uploaded_map.jpg")
    @patch("app.api.manifestations.validate_upload_file", return_value="image/jpeg")
    def test_add_map_attachment_multipart_upload(self, mock_validate, mock_save, client, normal_user_headers, sample_book_hierarchy):
        m_id = sample_book_hierarchy["manifestation_id"]
        fake_file = (io.BytesIO(b"fake image bytes"), "middle_earth.jpg")

        res = client.post(
            f"/api/manifestations/{m_id}/map-attachments",
            data={
                "title": "Uploaded Cloth Map",
                "type": "cloth_map",
                "file": fake_file,
            },
            content_type="multipart/form-data",
            headers=normal_user_headers,
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["title"] == "Uploaded Cloth Map"
        assert data["type"] == "cloth_map"
        assert data["image_url"] == "/static/gallery/uploaded_map.jpg"

    def test_add_map_attachment_rejects_dangerous_urls(self, client, normal_user_headers, sample_book_hierarchy):
        m_id = sample_book_hierarchy["manifestation_id"]
        for bad_url in [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "//evil.com/map.jpg",
            "/invalid/internal/path.jpg",
        ]:
            res = client.post(
                f"/api/manifestations/{m_id}/map-attachments",
                json={"title": "Bad Map", "type": "world_map", "image_url": bad_url},
                headers=normal_user_headers,
            )
            assert res.status_code == 400
            assert "error" in res.get_json()

    def test_add_map_attachment_audit_log_and_bounds(self, client, normal_user_headers, sample_book_hierarchy, app):
        from app.db.models import EntityAuditLog, db

        m_id = sample_book_hierarchy["manifestation_id"]

        # Rejects oversized title
        res = client.post(
            f"/api/manifestations/{m_id}/map-attachments",
            json={"title": "A" * 201, "type": "world_map"},
            headers=normal_user_headers,
        )
        assert res.status_code == 400

        # Successfully creates valid attachment and records audit log
        res = client.post(
            f"/api/manifestations/{m_id}/map-attachments",
            json={
                "title": "Valid Audit Map",
                "type": "world_map",
                "scale": "1:50,000",
                "projection": "Mercator",
                "image_url": "https://example.com/valid.jpg",
            },
            headers=normal_user_headers,
        )
        assert res.status_code == 201
        att_id = res.get_json()["data"]["id"]

        with app.app_context():
            logs = db.session.query(EntityAuditLog).filter_by(entity_type="manifestation", entity_id=m_id).all()
            assert any(log.change_type == "map_attachment_added" for log in logs)

        # Deleting also records audit log
        del_res = client.delete(
            f"/api/manifestations/{m_id}/map-attachments/{att_id}",
            headers=normal_user_headers,
        )
        assert del_res.status_code == 200

        with app.app_context():
            logs = db.session.query(EntityAuditLog).filter_by(entity_type="manifestation", entity_id=m_id).all()
            assert any(log.change_type == "map_attachment_deleted" for log in logs)


class TestItemMapInsertPresentAPI:
    """Test tracking map insert completeness on physical items."""

    def test_update_item_map_insert_present(self, client, normal_user_headers, sample_book_hierarchy):
        item_id = sample_book_hierarchy["item_id"]

        # Set map_insert_present to True
        res = client.put(
            f"/api/items/{item_id}",
            json={"map_insert_present": True},
            headers=normal_user_headers,
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["map_insert_present"] is True

        # Fetch item detail
        get_res = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
        assert get_res.status_code == 200
        assert get_res.get_json()["data"]["map_insert_present"] is True

        # Set map_insert_present to False (e.g. missing insert)
        res2 = client.patch(
            f"/api/items/{item_id}",
            json={"map_insert_present": False},
            headers=normal_user_headers,
        )
        assert res2.status_code == 200
        assert res2.get_json()["data"]["map_insert_present"] is False


# ===========================================================================
# 3. Meta Display Projection Tests
# ===========================================================================


class TestCartographicMetaDisplay:
    """Test display projection for cartographic properties and attachments."""

    def test_display_projection_includes_cartographic_fields(self):
        meta = {
            "format": "cartographic_map",
            "map_scale": "1:50000",
            "map_projection": "Transverse Mercator",
            "map_attachments": [
                {
                    "id": "att1",
                    "title": "Trail Map Insert",
                    "type": "topographic",
                    "image_url": "https://example.com/map.jpg",
                }
            ],
        }
        item_meta = {"map_insert_present": True}

        projection = build_display_projection(meta, item_meta)
        fields = projection["fields"]
        sections = projection["sections"]

        assert fields["map_scale"] == "1:50000"
        assert fields["map_projection"] == "Transverse Mercator"
        assert fields["has_map"] is True
        assert len(fields["map_attachments"]) == 1
        assert fields["map_insert_present"] is True

        assert sections["map_scale"] == "1:50000"
        assert sections["map_projection"] == "Transverse Mercator"
        assert sections["has_map"] is True
        assert sections["map_insert_present"] is True


# ===========================================================================
# 4. RDF Serialization Tests
# ===========================================================================


class TestCartographicRDFSerialization:
    """Test RDF triple generation for cartographic and map attachment entities."""

    def test_serialization_emits_cartographic_and_attachment_triples(self):
        items = [
            {
                "id": "item-map-1",
                "manifestation_id": "m-map-1",
                "expression_id": "e-map-1",
                "work_id": "w-map-1",
                "title": "Ordnance Survey Explorer Map",
                "content_type": "text",
                "format": "cartographic_map",
                "map_scale": "1:25000",
                "map_projection": "National Grid",
                "map_attachments": [
                    {
                        "title": "Footpaths and Bridleways Inset",
                        "type": "topographic",
                        "image_url": "https://example.com/inset.jpg",
                    }
                ],
                "map_insert_present": True,
            }
        ]

        ttl = serialize_collection_to_rdf(items, "http://testserver", output_format="turtle")
        g = Graph()
        g.parse(data=ttl, format="turtle")

        m_uri = URIRef("http://testserver/manifestations/m-map-1")
        i_uri = URIRef("http://testserver/items/item-map-1")

        # Cartographic properties on Manifestation
        assert (m_uri, IQOQO.mapScale, Literal("1:25000", datatype=XSD.string)) in g
        assert (m_uri, IQOQO.mapProjection, Literal("National Grid", datatype=XSD.string)) in g
        assert (m_uri, RDF.type, SCHEMA.Map) in g

        # Map attachment object
        att_nodes = list(g.objects(m_uri, IQOQO.hasMapAttachment))
        assert len(att_nodes) == 1
        att_node = att_nodes[0]
        assert (att_node, RDF.type, IQOQO.MapAttachment) in g
        assert (att_node, IQOQO.mapTitle, Literal("Footpaths and Bridleways Inset", datatype=XSD.string)) in g
        assert (att_node, IQOQO.mapType, Literal("topographic", datatype=XSD.string)) in g
        assert (att_node, IQOQO.mapImageUrl, Literal("https://example.com/inset.jpg", datatype=XSD.string)) in g

        # Cartographic Item property
        assert (i_uri, IQOQO.mapInsertPresent, Literal(True, datatype=XSD.boolean)) in g


# ===========================================================================
# 5. SHACL Shape Validation Tests
# ===========================================================================


class TestCartographicSHACLValidation:
    """Validate SHACL shape constraints for MapAttachment and Item insert completeness."""

    def test_valid_cartographic_graph_conforms(self):
        clear_cache()
        g = Graph()
        w = URIRef("https://iqoqo.org/works/w1")
        e = URIRef("https://iqoqo.org/expressions/e1")
        m = URIRef("https://iqoqo.org/manifestations/m1")
        att = URIRef("https://iqoqo.org/maps/att1")
        item = URIRef("https://iqoqo.org/items/i1")

        g.add((w, RDF.type, FRBR.Work))
        g.add((w, RDF.type, IQOQO.Work))
        g.add((w, SCHEMA.name, Literal("Middle-earth", datatype=XSD.string)))

        g.add((e, RDF.type, FRBR.Expression))
        g.add((e, RDF.type, IQOQO.Expression))
        g.add((e, FRBRER.expressionOf, w))
        g.add((e, SCHEMA.name, Literal("Middle-earth", datatype=XSD.string)))

        g.add((m, RDF.type, FRBR.Manifestation))
        g.add((m, RDF.type, IQOQO.Manifestation))
        g.add((m, FRBRER.embodimentOf, e))
        g.add((m, SCHEMA.name, Literal("Middle-earth Atlas", datatype=XSD.string)))
        g.add((m, IQOQO.mapScale, Literal("1:50000", datatype=XSD.string)))
        g.add((m, IQOQO.mapProjection, Literal("Mercator", datatype=XSD.string)))
        g.add((m, IQOQO.hasMapAttachment, att))

        g.add((att, RDF.type, IQOQO.MapAttachment))
        g.add((att, IQOQO.mapTitle, Literal("World Map", datatype=XSD.string)))
        g.add((att, IQOQO.mapType, Literal("world_map", datatype=XSD.string)))

        g.add((item, RDF.type, FRBR.Item))
        g.add((item, RDF.type, IQOQO.Item))
        g.add((item, FRBRER.exemplarOf, m))
        g.add((item, IQOQO.mapInsertPresent, Literal(True, datatype=XSD.boolean)))

        conforms, _, report = validate_graph(g)
        assert conforms is True, f"SHACL validation failed: {report}"

    def test_map_attachment_rejects_invalid_type(self):
        clear_cache()
        g = Graph()
        att = URIRef("https://iqoqo.org/maps/att2")
        g.add((att, RDF.type, IQOQO.MapAttachment))
        g.add((att, IQOQO.mapTitle, Literal("Invalid Type Map", datatype=XSD.string)))
        g.add((att, IQOQO.mapType, Literal("holographic_map", datatype=XSD.string)))

        conforms, _, report = validate_graph(g)
        assert conforms is False, "Expected SHACL failure for invalid mapType"
        assert "mapType" in report

    def test_map_insert_present_rejected_on_manifestation(self):
        clear_cache()
        g = Graph()
        e = URIRef("https://iqoqo.org/expressions/e2")
        m = URIRef("https://iqoqo.org/manifestations/m2")
        g.add((m, RDF.type, FRBR.Manifestation))
        g.add((m, RDF.type, IQOQO.Manifestation))
        g.add((m, FRBRER.embodimentOf, e))
        g.add((m, SCHEMA.name, Literal("Invalid Manifestation", datatype=XSD.string)))
        g.add((m, IQOQO.mapInsertPresent, Literal(True, datatype=XSD.boolean)))

        conforms, _, report = validate_graph(g)
        assert conforms is False, "Expected SHACL failure when mapInsertPresent is attached to Manifestation"
        assert "mapInsertPresent" in report
