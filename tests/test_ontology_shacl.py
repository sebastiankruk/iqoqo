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

import pytest

pyshacl = pytest.importorskip("pyshacl")
rdflib = pytest.importorskip("rdflib")

from rdflib import Graph, Literal, Namespace, URIRef  # noqa: E402
from rdflib.namespace import RDF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IQOQO = Namespace("https://iqoqo.org/ontology#")


def _load_shapes_graph() -> Graph:
    shapes = Graph()
    shapes.parse(ROOT / "docs" / "ontology" / "iqoqo-shapes.ttl", format="turtle")
    shapes.parse(ROOT / "docs" / "ontology" / "iqoqo.ttl", format="turtle")
    return shapes


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
    conforms, _, _ = pyshacl.validate(
        data_graph=_build_data_graph(expansion_aggregated=False),
        shacl_graph=_load_shapes_graph(),
        ont_graph=None,
        inference="rdfs",
        abort_on_first=False,
    )
    assert conforms is True


def test_shacl_expansion_aggregated_into_container_fails():
    """An expansion Work aggregated into an F16 Container Work violates the shape."""
    conforms, _, report = pyshacl.validate(
        data_graph=_build_data_graph(expansion_aggregated=True),
        shacl_graph=_load_shapes_graph(),
        ont_graph=None,
        inference="rdfs",
        abort_on_first=False,
    )
    assert conforms is False
    assert "Expansion Work must not be aggregated" in report
