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
"""Data sovereignty export service for user collections.

Supports chunked streaming serialization into canonical JSON-LD, RDF Turtle,
and hierarchical JSON adhering strictly to the FRBR Group 1 ontology
(Item -> Manifestation -> Expression -> Work) and Schema.org / Dublin Core standards.
"""

import itertools
import json
import logging
import uuid
from collections.abc import Generator, Iterable
from typing import Any

from rdflib import Graph, Namespace
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.iri import get_lod_base_url as _get_lod_base_url
from app.db.core import Expression, Item, Manifestation, db

logger = logging.getLogger(__name__)

# RDF Namespaces
FRBR_PURL = Namespace("http://purl.org/vocab/frbr/core#")
FRBR_IFLA = Namespace("http://iflastandards.info/ns/frbr/frbrer/")
SCHEMA = Namespace("https://schema.org/")
DC = Namespace("http://purl.org/dc/terms/")
IQOQO = Namespace("https://iqoqo.org/ontology#")

# Canonical JSON-LD @context dictionary
CANONICAL_JSONLD_CONTEXT: dict[str, Any] = {
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "frbr": "http://purl.org/vocab/frbr/core#",
    "frbrer": "http://iflastandards.info/ns/frbr/frbrer/",
    "schema": "https://schema.org/",
    "dc": "http://purl.org/dc/terms/",
    "iqoqo": "https://iqoqo.org/ontology#",
    "Work": "frbr:Work",
    "Expression": "frbr:Expression",
    "Manifestation": "frbr:Manifestation",
    "Item": "frbr:Item",
    "title": "dc:title",
    "creator": "frbrer:creator",
    "author": "schema:author",
    "contributor": "schema:contributor",
    "performer": "schema:performer",
    "name": "schema:name",
    "language": "dc:language",
    "isbn": "schema:isbn",
    "publisher": "schema:publisher",
    "format": "schema:bookFormat",
    "exemplarOf": {"@id": "frbrer:exemplarOf", "@type": "@id"},
    "embodimentOf": {"@id": "frbrer:embodimentOf", "@type": "@id"},
    "expressionOf": {"@id": "frbrer:expressionOf", "@type": "@id"},
    "isPartOf": {"@id": "schema:isPartOf", "@type": "@id"},
    "hasPart": {"@id": "schema:hasPart", "@type": "@id"},
    "wasDerivedFrom": {"@id": "http://www.w3.org/ns/prov#wasDerivedFrom", "@type": "@id"},
    "image": {"@id": "schema:image", "@type": "@id"},
    "datePublished": {"@id": "schema:datePublished"},
    "startDate": {"@id": "schema:startDate"},
    "location": {"@id": "schema:location"},
    "itemCondition": {"@id": "schema:itemCondition", "@type": "@id"},
    "status": "iqoqo:status",
    "prov": "http://www.w3.org/ns/prov#",
}


class ExportService:
    """Service providing streaming exports of user collections in Linked Data and JSON formats."""

    @classmethod
    def get_lod_base_url(cls, base_url: str | None = None) -> str:
        """Resolve canonical base URL for Linked Data entity IRIs."""
        if base_url:
            return base_url.rstrip("/")
        return _get_lod_base_url().rstrip("/")

    @classmethod
    def build_batch_rdf_graph(
        cls,
        items: list[Item],
        base_url: str,
    ) -> Graph:
        """
        Build an RDF Graph for a batch of Items adhering to FRBRer and Schema.org shapes.

        Ensures physical attributes (like isbn13) attach strictly to Manifestations, never to Works,
        and enriches with contributors, work parts, image scans, and user collections.
        """
        from app.core.frbr_service import build_collection_rdf_graph

        graph = build_collection_rdf_graph(items, base_url, enrichment_profile="full")
        graph.bind("frbr", FRBR_PURL)
        graph.bind("frbrer", FRBR_IFLA)
        graph.bind("schema", SCHEMA)
        graph.bind("dc", DC)
        graph.bind("iqoqo", IQOQO)

        return graph

    @classmethod
    def stream_jsonld(
        cls,
        items_iterable: Iterable[Item],
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """Stream JSON-LD generated from the same enriched RDF graph as Turtle/NT."""
        resolved_base_url = cls.get_lod_base_url(base_url)
        yield '{\n  "@context": ' + json.dumps(CANONICAL_JSONLD_CONTEXT, indent=2) + ',\n  "@graph": [\n'

        iterator = iter(items_iterable)
        first_node = True
        while True:
            batch = list(itertools.islice(iterator, batch_size))
            if not batch:
                break
            graph = cls.build_batch_rdf_graph(batch, resolved_base_url)
            serialized = graph.serialize(format="json-ld", context=CANONICAL_JSONLD_CONTEXT, auto_compact=True)
            data = json.loads(serialized)
            if isinstance(data, dict):
                nodes = data.get("@graph", [data])
            else:
                nodes = data
            for node in nodes:
                if not first_node:
                    yield ",\n"
                first_node = False
                yield "    " + json.dumps(node, ensure_ascii=False, separators=(",", ": "))

        yield "\n  ]\n}\n"

    @classmethod
    def _stream_jsonld_legacy(
        cls,
        items_iterable: Iterable[Item],
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """Stream canonical JSON-LD collection representation chunk by chunk."""
        resolved_base_url = cls.get_lod_base_url(base_url)

        # 1. Yield JSON-LD header with @context and opening of @graph
        context_str = json.dumps({"@context": CANONICAL_JSONLD_CONTEXT}, indent=2)
        # Strip trailing closing brace and append @graph array opening
        header = context_str[:-2] + ',\n  "@graph": [\n'
        yield header

        iterator = iter(items_iterable)
        seen_entity_iris: set[str] = set()
        first_node = True

        while True:
            batch = list(itertools.islice(iterator, batch_size))
            if not batch:
                break

            for item in batch:
                m = item.manifestation
                expr = m.expression if m else None
                work = expr.work if expr else None

                item_id = item.id
                m_id = m.id if m else item_id
                e_id = expr.id if expr else m_id
                w_id = work.id if work else e_id

                i_iri = f"{resolved_base_url}/items/{item_id}"
                m_iri = f"{resolved_base_url}/manifestations/{m_id}"
                e_iri = f"{resolved_base_url}/expressions/{e_id}"
                w_iri = f"{resolved_base_url}/works/{w_id}"

                nodes_to_emit: list[dict[str, Any]] = []

                # Work node
                if w_iri not in seen_entity_iris:
                    seen_entity_iris.add(w_iri)
                    w_title = (work.title if work else getattr(m, "title", "Untitled")) or "Untitled"
                    authors: list[str] = []
                    if work and work.meta and isinstance(work.meta, dict):
                        raw_authors = work.meta.get("authors") or work.meta.get("Authors")
                        if isinstance(raw_authors, list):
                            authors = [str(a) for a in raw_authors if a]
                        elif isinstance(raw_authors, str) and raw_authors.strip():
                            authors = [raw_authors.strip()]
                    if not authors and m and m.meta and isinstance(m.meta, dict):
                        raw_authors = m.meta.get("authors") or m.meta.get("Authors") or m.meta.get("author")
                        if isinstance(raw_authors, list):
                            authors = [str(a) for a in raw_authors if a]
                        elif isinstance(raw_authors, str) and raw_authors.strip():
                            authors = [raw_authors.strip()]
                    primary_author = authors[0] if authors else "Unknown"

                    w_node: dict[str, Any] = {
                        "@id": w_iri,
                        "@type": ["frbr:Work", "frbrer:Work", "schema:CreativeWork"],
                        "title": w_title,
                        "schema:name": w_title,
                        "creator": primary_author,
                        "schema:author": primary_author,
                        "http://iflastandards.info/ns/frbr/frbrer/creator": primary_author,
                    }
                    nodes_to_emit.append(w_node)

                # Expression node
                if e_iri not in seen_entity_iris:
                    seen_entity_iris.add(e_iri)
                    e_node: dict[str, Any] = {
                        "@id": e_iri,
                        "@type": ["frbr:Expression", "frbrer:Expression"],
                        "expressionOf": w_iri,
                    }
                    if expr and expr.language:
                        e_node["language"] = expr.language
                        e_node["schema:inLanguage"] = expr.language
                    nodes_to_emit.append(e_node)

                # Manifestation node
                if m_iri not in seen_entity_iris:
                    seen_entity_iris.add(m_iri)
                    m_title = (m.title if m else getattr(work, "title", "Untitled")) or "Untitled"
                    m_node: dict[str, Any] = {
                        "@id": m_iri,
                        "@type": ["frbr:Manifestation", "frbrer:Manifestation", "schema:CreativeWork"],
                        "embodimentOf": e_iri,
                        "title": m_title,
                        "schema:name": m_title,
                    }
                    if m:
                        # Physical attributes strictly on Manifestation
                        if m.isbn13 and len(m.isbn13) == 13 and m.isbn13.isdigit():
                            m_node["isbn"] = m.isbn13
                        if m.publisher:
                            m_node["publisher"] = m.publisher
                        if m.publication_date:
                            m_node["schema:datePublished"] = str(m.publication_date)
                        if m.format or m.format_type:
                            m_node["format"] = m.format or m.format_type
                    nodes_to_emit.append(m_node)

                # Item node
                if i_iri not in seen_entity_iris:
                    seen_entity_iris.add(i_iri)
                    i_node: dict[str, Any] = {
                        "@id": i_iri,
                        "@type": ["frbr:Item", "frbrer:Item"],
                        "exemplarOf": m_iri,
                    }
                    if item.condition:
                        i_node["schema:itemCondition"] = item.condition
                    if item.status:
                        i_node["iqoqo:status"] = item.status
                    nodes_to_emit.append(i_node)

                # Emit nodes
                for node in nodes_to_emit:
                    chunk = ""
                    if not first_node:
                        chunk += ",\n"
                    first_node = False
                    node_json = json.dumps(node, indent=4)
                    indented_lines = ["    " + line for line in node_json.split("\n")]
                    chunk += "\n".join(indented_lines)
                    yield chunk

        # 3. Yield JSON-LD closing
        yield "\n  ]\n}\n"

    @classmethod
    def stream_turtle(
        cls,
        items_iterable: Iterable[Item],
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """Stream RDF Turtle collection representation chunk by chunk."""
        resolved_base_url = cls.get_lod_base_url(base_url)
        iterator = iter(items_iterable)
        first_chunk = True

        while True:
            batch = list(itertools.islice(iterator, batch_size))
            if not batch:
                break

            graph = cls.build_batch_rdf_graph(batch, resolved_base_url)
            ttl_data = graph.serialize(format="turtle")
            if not ttl_data:
                continue

            if first_chunk:
                first_chunk = False
                yield ttl_data
            else:
                # Strip prefix declarations from subsequent chunks
                lines = [
                    line for line in ttl_data.splitlines(keepends=True) if not (line.startswith("@prefix") or line.startswith("PREFIX"))
                ]
                filtered = "".join(lines).lstrip()
                if filtered:
                    yield filtered

        if first_chunk:
            # If empty collection, output empty graph prefixes
            empty_g = Graph()
            empty_g.bind("frbr", FRBR_PURL)
            empty_g.bind("frbrer", FRBR_IFLA)
            empty_g.bind("schema", SCHEMA)
            empty_g.bind("dc", DC)
            empty_g.bind("iqoqo", IQOQO)
            yield empty_g.serialize(format="turtle")

    @classmethod
    def stream_ntriples(
        cls,
        items_iterable: Iterable[Item],
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """Stream N-Triples batches from the canonical enriched RDF graph."""
        resolved_base_url = cls.get_lod_base_url(base_url)
        iterator = iter(items_iterable)
        while True:
            batch = list(itertools.islice(iterator, batch_size))
            if not batch:
                break
            payload = cls.build_batch_rdf_graph(batch, resolved_base_url).serialize(format="nt")
            if payload:
                yield payload

    @classmethod
    def stream_json(
        cls,
        items_iterable: Iterable[Item],
    ) -> Generator[str, None, None]:
        """Stream hierarchical JSON collection representation chunk by chunk."""
        yield "[\n"
        first_item = True

        for item in items_iterable:
            m = item.manifestation
            expr = m.expression if m else None
            work = expr.work if expr else None

            item_dict: dict[str, Any] = {
                "id": item.id,
                "status": item.status,
                "collection_status": item.collection_status,
                "condition": item.condition,
                "is_hidden": item.is_hidden,
                "added_at": item.added_at.isoformat() if hasattr(item.added_at, "isoformat") and item.added_at else None,
                "updated_at": item.updated_at.isoformat() if hasattr(item.updated_at, "isoformat") and item.updated_at else None,
                "manifestation": None,
            }

            if m:
                work_dict: dict[str, Any] | None = None
                if expr and work:
                    authors: list[str] = []
                    if work.meta and isinstance(work.meta, dict):
                        raw_authors = work.meta.get("authors") or work.meta.get("Authors")
                        if isinstance(raw_authors, list):
                            authors = [str(a) for a in raw_authors if a]
                        elif isinstance(raw_authors, str) and raw_authors.strip():
                            authors = [raw_authors.strip()]
                    work_dict = {
                        "id": work.id,
                        "title": work.title,
                        "sort_title": work.sort_title,
                        "authors": authors,
                    }

                expr_dict: dict[str, Any] | None = None
                if expr:
                    expr_dict = {
                        "id": expr.id,
                        "content_type": expr.content_type,
                        "language": expr.language,
                        "kind": expr.kind,
                        "work": work_dict,
                    }

                item_dict["manifestation"] = {
                    "id": m.id,
                    "title": m.title,
                    "isbn13": m.isbn13,
                    "upc": m.upc,
                    "ean": m.ean,
                    "publisher": m.publisher,
                    "publication_date": str(m.publication_date) if m.publication_date else None,
                    "cover_url": m.cover_url,
                    "format": m.format,
                    "format_type": m.format_type,
                    "expression": expr_dict,
                }

            chunk = ""
            if not first_item:
                chunk += ",\n"
            first_item = False

            item_json = json.dumps(item_dict, indent=2)
            indented = ["  " + line for line in item_json.split("\n")]
            chunk += "\n".join(indented)
            yield chunk

        yield "\n]\n"

    @classmethod
    def stream_export(
        cls,
        items_iterable: Iterable[Item],
        export_format: str = "json-ld",
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """Route to format-specific streaming generator."""
        fmt = export_format.lower().strip()
        if fmt == "json-ld":
            yield from cls.stream_jsonld(items_iterable, batch_size=batch_size, base_url=base_url)
        elif fmt == "turtle":
            yield from cls.stream_turtle(items_iterable, batch_size=batch_size, base_url=base_url)
        elif fmt in {"nt", "n-triples"}:
            yield from cls.stream_ntriples(items_iterable, batch_size=batch_size, base_url=base_url)
        elif fmt == "json":
            yield from cls.stream_json(items_iterable)
        else:
            raise ValueError(f"Unsupported export format '{fmt}'. Supported: json-ld, turtle, nt, json")

    @classmethod
    def stream_user_collection(
        cls,
        user_id: uuid.UUID | str,
        export_format: str = "json-ld",
        batch_size: int = 100,
        base_url: str | None = None,
    ) -> Generator[str, None, None]:
        """
        Stream user's library items with batched cursor querying (yield_per).

        Eagerly loads Item -> Manifestation -> Expression -> Work relationships.
        """
        # Ensure user_id is UUID instance if applicable
        resolved_uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

        stmt = (
            select(Item)
            .where(Item.owner_id == resolved_uid)
            .options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
            .execution_options(yield_per=batch_size)
            .order_by(Item.id.asc())
        )

        items_iterable = db.session.execute(stmt).scalars()
        yield from cls.stream_export(
            items_iterable=items_iterable,
            export_format=export_format,
            batch_size=batch_size,
            base_url=base_url,
        )
