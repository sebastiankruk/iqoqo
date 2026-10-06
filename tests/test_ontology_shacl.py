"""SHACL validation tests for the iqoqo ontology."""

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

from pathlib import Path
from typing import cast

import pytest

pyshacl = pytest.importorskip("pyshacl")
rdflib = pytest.importorskip("rdflib")  # noqa: F401

from rdflib import Graph, Literal, Namespace, URIRef  # noqa: E402
from rdflib.namespace import RDF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IQOQO = Namespace("https://iqoqo.org/ontology#")


def _parse(path: Path) -> Graph:
    """Parse a turtle file into a fresh graph.

    @param path: The .ttl file to read.
    @returns: The parsed graph.
    """
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


# Parsed once per session. The two ontology files are static inputs and cost
# 18.7 ms and 22.4 ms to parse respectively; with 8 tests each validating, that
# was 0.53 s of re-parsing.
#
# The cached graph is the *pristine* parse and is never handed to pyshacl
# directly. pyshacl mutates the shapes graph it is given -- it materialises RDFS
# inferences into it, taking it from 387 to 389 triples on the first call and
# staying there. Caching the live object would therefore leak inferred triples
# from one test into the next, which could make a SHACL shape appear to pass for
# the wrong reason. Every caller gets a copy instead.
_SHAPES = _parse(ROOT / "docs" / "ontology" / "iqoqo-shapes.ttl")
_ONTOLOGY = _parse(ROOT / "docs" / "ontology" / "iqoqo.ttl")


def _copy(graph: Graph) -> Graph:
    """Return an independent copy of a cached graph.

    @param graph: The graph to copy.
    @returns: A new graph with the same triples.
    """
    return Graph() + graph


def _load_shapes_graph() -> Graph:
    return _copy(_SHAPES)


def _load_ontology_graph() -> Graph:
    """The OWL vocabulary (iqoqo.ttl), used for RDFS inference (e.g. Work ⊑ F1_Work)."""
    return _copy(_ONTOLOGY)


def _validate(data: Graph) -> tuple[bool, Graph, str]:
    return cast(
        "tuple[bool, Graph, str]",
        pyshacl.validate(
            data_graph=data,
            shacl_graph=_load_shapes_graph(),
            ont_graph=_load_ontology_graph(),
            inference="rdfs",
            abort_on_first=False,
        ),
    )


def _build_data_graph(expansion_aggregated: bool = False) -> Graph:
    data = Graph()
    data.bind("iqoqo", IQOQO)

    base_work = URIRef("https://iqoqo.org/ontology#baseWork1")
    expansion_work = URIRef("https://iqoqo.org/ontology#expansionWork1")
    container_work = URIRef("https://iqoqo.org/ontology#containerWork1")
    container_agg = URIRef("https://iqoqo.org/ontology#containerAgg1")

    data.add((base_work, RDF.type, IQOQO.Work))
    data.add((expansion_work, RDF.type, IQOQO.Work))
    data.add((container_work, RDF.type, IQOQO.Work))

    # Expansion link
    data.add((expansion_work, IQOQO.is_expansion_of, base_work))

    if expansion_aggregated:
        data.add((container_agg, RDF.type, IQOQO.ContainerAggregation))
        data.add((container_agg, IQOQO.containerWork, container_work))
        data.add((container_agg, IQOQO.aggregatedWork, expansion_work))

    return data


def test_shacl_expansion_without_container_conforms():
    """An expansion Work not aggregated into a container conforms to the shape."""
    conforms, _, _ = _validate(_build_data_graph(expansion_aggregated=False))
    assert conforms is True


def test_shacl_expansion_aggregated_into_container_fails():
    """An expansion Work aggregated into an F16 Container Work violates the shape."""
    conforms, _, report = _validate(_build_data_graph(expansion_aggregated=True))
    assert conforms is False
    assert "Expansion Work must not be aggregated" in report


def _build_link_graph(link_type: str | None = "is_expansion_of", self_link: bool = False) -> Graph:
    """Data graph with a reified WorkExpansionLink (used by link-shape tests)."""
    data = Graph()
    data.bind("iqoqo", IQOQO)

    base_work = URIRef("https://iqoqo.org/ontology#baseWork1")
    expansion_work = URIRef("https://iqoqo.org/ontology#expansionWork1")
    if self_link:
        expansion_work = base_work
    link = URIRef("https://iqoqo.org/ontology#workExpansionLink1")

    data.add((base_work, RDF.type, IQOQO.Work))
    data.add((expansion_work, RDF.type, IQOQO.Work))
    data.add((link, RDF.type, IQOQO.WorkExpansionLink))
    data.add((link, IQOQO.baseWork, base_work))
    data.add((link, IQOQO.expansionWork, expansion_work))
    if link_type is not None:
        data.add((link, IQOQO.link_type, Literal(link_type)))
    return data


def test_work_expansion_link_shape_valid_conforms():
    """A well-formed WorkExpansionLink with the controlled link type conforms."""
    conforms, _, report = _validate(_build_link_graph())
    assert conforms is True, report


def test_work_expansion_link_shape_rejects_unknown_link_type():
    """link_type outside the controlled lexicon violates WorkExpansionLinkShape."""
    conforms, _, report = _validate(_build_link_graph(link_type="is_sequel_to"))
    assert conforms is False
    assert "link_type must be one of the controlled lexicon" in report


def test_work_expansion_link_shape_rejects_self_link():
    """baseWork == expansionWork violates the SPARQL constraint."""
    conforms, _, report = _validate(_build_link_graph(self_link=True))
    assert conforms is False
    assert "cannot be its own expansion" in report


def _build_container_aggregation_graph(with_work: bool, with_item: bool) -> Graph:
    """Data graph with a single ContainerAggregation node."""
    data = Graph()
    data.bind("iqoqo", IQOQO)

    container_work = URIRef("https://iqoqo.org/ontology#containerWork1")
    container_agg = URIRef("https://iqoqo.org/ontology#containerAgg1")
    aggregated_work = URIRef("https://iqoqo.org/ontology#aggregatedWork1")
    aggregated_item = URIRef("https://iqoqo.org/ontology#aggregatedItem1")

    data.add((container_work, RDF.type, IQOQO.Work))
    data.add((container_agg, RDF.type, IQOQO.ContainerAggregation))
    data.add((container_agg, IQOQO.containerWork, container_work))
    if with_work:
        data.add((aggregated_work, RDF.type, IQOQO.Work))
        data.add((container_agg, IQOQO.aggregatedWork, aggregated_work))
    if with_item:
        data.add((aggregated_item, RDF.type, IQOQO.Item))
        data.add((container_agg, IQOQO.aggregatedItem, aggregated_item))
    return data


def test_container_aggregation_with_work_component_conforms():
    """An F16 aggregation with a Work component (and only a Work) conforms."""
    conforms, _, report = _validate(_build_container_aggregation_graph(with_work=True, with_item=False))
    assert conforms is True, report


def test_container_aggregation_requires_at_least_one_aggregate():
    """A ContainerAggregation with no aggregated Work or Item violates sh:or."""
    conforms, _, _ = _validate(_build_container_aggregation_graph(with_work=False, with_item=False))
    assert conforms is False


def test_container_aggregation_rejects_item_as_aggregated_work():
    """aggregatedWork must be a Work; binding an Item node fails the shape.

    Uses inference="none" with explicit FRBR typing because the OWL vocabulary
    declares ``iqoqo:aggregatedWork rdfs:range iqoqo:Work`` — under RDFS
    inference the range axiom would (correctly) type the Item as a Work.
    """
    data = Graph()
    data.bind("iqoqo", IQOQO)
    FRBROO = Namespace("http://iflastandards.info/ns/fr/frbr/frbroo/")

    container_work = URIRef("https://iqoqo.org/ontology#containerWork1")
    container_agg = URIRef("https://iqoqo.org/ontology#containerAgg1")
    item = URIRef("https://iqoqo.org/ontology#aggregatedItem1")

    data.add((container_work, RDF.type, IQOQO.Work))
    data.add((container_work, RDF.type, FRBROO.F1_Work))
    data.add((container_agg, RDF.type, IQOQO.ContainerAggregation))
    data.add((container_agg, IQOQO.containerWork, container_work))
    data.add((item, RDF.type, IQOQO.Item))
    data.add((item, RDF.type, FRBROO.F5_Item))
    data.add((container_agg, IQOQO.aggregatedWork, item))

    conforms, _, report = pyshacl.validate(
        data_graph=data,
        shacl_graph=_load_shapes_graph(),
        ont_graph=None,
        inference="none",
        abort_on_first=False,
    )
    assert conforms is False
    assert "aggregatedWork must be of type Work" in report


def test_cached_ontology_graphs_are_never_handed_out_directly():
    """The session cache must survive pyshacl mutating the graph it receives.

    pyshacl materialises RDFS inferences into the shapes graph it is given --
    387 triples become 389 on the first call. A cache that handed out the live
    object would leak those inferred triples into every later test, where a
    shape could pass or fail for a reason that has nothing to do with the data
    under test. This asserts each caller receives an independent, pristine graph.

    @returns: Nothing; a shared or already-mutated graph fails the test.
    """
    pristine_shapes = len(_SHAPES)

    first = _load_shapes_graph()
    assert len(first) == pristine_shapes, "the cached graph was already mutated"

    # Hand it to pyshacl and let it do whatever it does to it.
    data = _build_data_graph(expansion_aggregated=True)
    _validate(data)

    second = _load_shapes_graph()
    assert len(second) == pristine_shapes, "inferred triples leaked into the next caller"
    assert len(_SHAPES) == pristine_shapes, "the cache itself was mutated"

    # And the two callers are genuinely independent objects.
    assert first is not second


def test_each_validation_gets_its_own_graph():
    """Two validations must not share a graph object.

    @returns: Nothing; a shared object fails the test.
    """
    a = _load_shapes_graph()
    b = _load_shapes_graph()
    assert a is not b, "callers share one Graph instance"

    c = _load_ontology_graph()
    d = _load_ontology_graph()
    assert c is not d, "callers share one ontology Graph instance"
