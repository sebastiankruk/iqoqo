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
"""SHACL validation service for RDF graphs against iqoqo shapes."""

import os
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph

# Path to the SHACL shapes file
SHAPES_PATH = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "docs" / "ontology" / "iqoqo-shapes.ttl"

_shapes_graph: Graph | None = None


def _get_shapes_graph() -> Graph:
    """Load and cache the SHACL shapes graph."""
    global _shapes_graph  # noqa: PLW0603  # pylint: disable=global-statement
    if _shapes_graph is None:
        _shapes_graph = Graph()
        _shapes_graph.parse(str(SHAPES_PATH), format="turtle")
    return _shapes_graph


def validate_graph(data_graph: Graph) -> tuple[bool, Graph, str]:
    """
    Validate an RDF data graph against iqoqo SHACL shapes.

    Args:
        data_graph: The RDF graph to validate.

    Returns:
        Tuple of (conforms: bool, results_graph: Graph, results_text: str)
    """
    shapes_graph = _get_shapes_graph()
    conforms, results_graph, results_text = shacl_validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
    )
    return conforms, results_graph, results_text


def validate_rdf_string(rdf_data: str, rdf_format: str = "turtle") -> tuple[bool, str]:
    """
    Validate an RDF string against iqoqo SHACL shapes.

    Args:
        rdf_data: The RDF data as a string.
        rdf_format: Format of the RDF data ('turtle' or 'json-ld').

    Returns:
        Tuple of (conforms: bool, results_text: str)
    """
    data_graph = Graph()
    data_graph.parse(data=rdf_data, format=rdf_format)
    conforms, _, results_text = validate_graph(data_graph)
    return conforms, results_text
