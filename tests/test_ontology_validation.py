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
"""Tests for Python-level ontology runtime validation guards."""

import pytest

from app.core.ontology_validation import (
    validate_container_not_linked_as_expansion,
    validate_work_not_expansion_aggregated,
)
from app.db.core import WORK_LINK_TYPE_IS_EXPANSION_OF, Work, WorkExpansionLink
from app.db.games import ContainerAggregation
from app.db.models import db


def test_validate_work_not_expansion_aggregated_passes_when_independent(app):
    """An independent Work with no expansion link passes validation."""
    with app.app_context():
        work = Work(title="Base Work Standalone")
        db.session.add(work)
        db.session.commit()

        # Should not raise
        validate_work_not_expansion_aggregated(work.id)


def test_validate_work_not_expansion_aggregated_raises_when_expansion(app):
    """A Work linked as an expansion of another Work raises ValueError on aggregation."""
    with app.app_context():
        base = Work(title="Catan Base Game")
        expansion = Work(title="Catan 5-6 Player Extension")
        db.session.add_all([base, expansion])
        db.session.commit()

        link = WorkExpansionLink(
            base_work_id=base.id,
            expansion_work_id=expansion.id,
            link_type=WORK_LINK_TYPE_IS_EXPANSION_OF,
        )
        db.session.add(link)
        db.session.commit()

        with pytest.raises(ValueError, match="is an expansion of .* and cannot be aggregated"):
            validate_work_not_expansion_aggregated(expansion.id)


def test_validate_container_not_linked_as_expansion_passes_when_not_container(app):
    """A standard non-container Work passes validation."""
    with app.app_context():
        work = Work(title="Regular Book Work")
        db.session.add(work)
        db.session.commit()

        # Should not raise
        validate_container_not_linked_as_expansion(work.id)


def test_validate_container_not_linked_as_expansion_raises_when_aggregating(app):
    """An F16 Container Work that aggregates components raises ValueError if declared as expansion."""
    with app.app_context():
        container = Work(title="Big Box Board Game")
        component = Work(title="Rulebook Work")
        db.session.add_all([container, component])
        db.session.commit()

        agg = ContainerAggregation(
            container_work_id=container.id,
            aggregated_type="work",
            aggregated_work_id=component.id,
            component_name="Rulebook",
            quantity=1,
        )
        db.session.add(agg)
        db.session.commit()

        with pytest.raises(ValueError, match="is an F16 Container Work and cannot be declared an expansion"):
            validate_container_not_linked_as_expansion(container.id)


def test_lego_shacl_validation_conforming():
    """Valid LEGO Manifestation and Item conform to SHACL shapes with zero violations."""
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    from app.core.shacl_service import clear_cache, validate_graph

    clear_cache()

    IQOQO = Namespace("https://iqoqo.org/ontology#")
    FRBR = Namespace("http://purl.org/vocab/frbr/core#")
    FRBRER = Namespace("http://iflastandards.info/ns/frbr/frbrer/")
    SCHEMA = Namespace("https://schema.org/")

    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("frbr", FRBR)
    g.bind("frbrer", FRBRER)
    g.bind("schema", SCHEMA)

    w = URIRef("https://iqoqo.org/works/101")
    e = URIRef("https://iqoqo.org/expressions/101")
    m = URIRef("https://iqoqo.org/manifestations/101")
    item = URIRef("https://iqoqo.org/items/101")

    # FRBR hierarchy
    g.add((w, RDF.type, FRBR.Work))
    g.add((e, RDF.type, FRBR.Expression))
    g.add((e, FRBRER.expressionOf, w))
    g.add((m, RDF.type, FRBR.Manifestation))
    g.add((m, RDF.type, IQOQO.Manifestation))
    g.add((m, FRBRER.embodimentOf, e))
    g.add((m, SCHEMA.name, Literal("Concorde")))
    g.add((item, RDF.type, FRBR.Item))
    g.add((item, RDF.type, IQOQO.Item))
    g.add((item, FRBRER.exemplarOf, m))

    # LEGO Manifestation attributes
    g.add((m, IQOQO.setNumber, Literal("10318-1", datatype=XSD.string)))
    g.add((m, IQOQO.pieceCount, Literal(2083, datatype=XSD.integer)))
    g.add((m, IQOQO.minifigCount, Literal(0, datatype=XSD.integer)))

    # LEGO Item attributes
    g.add((item, IQOQO.buildStatus, Literal("built", datatype=XSD.string)))
    g.add((item, IQOQO.missingPiecesCount, Literal(0, datatype=XSD.integer)))
    g.add((item, IQOQO.instructionsIncluded, Literal(True, datatype=XSD.boolean)))

    conforms, _, report = validate_graph(g)
    assert conforms is True, f"Expected conforming graph, got violations: {report}"


def test_lego_shacl_validation_rejects_build_status_on_work():
    """Attaching iqoqo:buildStatus directly to a Work is rejected by SHACL validation."""
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    from app.core.shacl_service import clear_cache, validate_graph

    clear_cache()

    IQOQO = Namespace("https://iqoqo.org/ontology#")
    FRBR = Namespace("http://purl.org/vocab/frbr/core#")

    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("frbr", FRBR)

    w = URIRef("https://iqoqo.org/works/102")
    g.add((w, RDF.type, FRBR.Work))
    g.add((w, RDF.type, IQOQO.Work))
    g.add((w, IQOQO.buildStatus, Literal("built", datatype=XSD.string)))

    conforms, _, report = validate_graph(g)
    assert conforms is False, "Expected SHACL failure when buildStatus is attached directly to a Work"
    assert "buildStatus" in report


def test_lego_shacl_validation_rejects_invalid_build_status():
    """Invalid buildStatus value violates SHACL controlled vocabulary constraint."""
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    from app.core.shacl_service import clear_cache, validate_graph

    clear_cache()

    IQOQO = Namespace("https://iqoqo.org/ontology#")
    FRBR = Namespace("http://purl.org/vocab/frbr/core#")

    g = Graph()
    item = URIRef("https://iqoqo.org/items/103")
    g.add((item, RDF.type, FRBR.Item))
    g.add((item, RDF.type, IQOQO.Item))
    g.add((item, IQOQO.buildStatus, Literal("invalid_status_value", datatype=XSD.string)))

    conforms, _, report = validate_graph(g)
    assert conforms is False, "Expected SHACL failure for invalid buildStatus value"
    assert "buildStatus" in report


def test_lego_shacl_validation_rejects_negative_piece_count():
    """Negative pieceCount violates sh:minInclusive 0 constraint."""
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    from app.core.shacl_service import clear_cache, validate_graph

    clear_cache()

    IQOQO = Namespace("https://iqoqo.org/ontology#")
    FRBR = Namespace("http://purl.org/vocab/frbr/core#")

    g = Graph()
    m = URIRef("https://iqoqo.org/manifestations/104")
    g.add((m, RDF.type, FRBR.Manifestation))
    g.add((m, RDF.type, IQOQO.Manifestation))
    g.add((m, IQOQO.pieceCount, Literal(-5, datatype=XSD.integer)))

    conforms, _, report = validate_graph(g)
    assert conforms is False, "Expected SHACL failure for negative pieceCount"
    assert "pieceCount" in report
