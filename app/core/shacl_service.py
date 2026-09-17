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
from typing import Any, Literal, overload

from pyshacl import validate as shacl_validate
from rdflib import Graph

# Paths to the SHACL shapes and ontology files
_ONTOLOGY_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "docs" / "ontology"
SHAPES_PATH = _ONTOLOGY_DIR / "iqoqo-shapes.ttl"
ONTOLOGY_PATH = _ONTOLOGY_DIR / "iqoqo.ttl"

_shapes_graph: Graph | None = None
_ontology_graph: Graph | None = None


def _get_shapes_graph() -> Graph:
    """Load and cache the SHACL shapes graph."""
    global _shapes_graph  # noqa: PLW0603  # pylint: disable=global-statement
    if _shapes_graph is None:
        _shapes_graph = Graph()
        _shapes_graph.parse(str(SHAPES_PATH), format="turtle")
    return _shapes_graph


def _get_ontology_graph() -> Graph:
    """Load and cache the OWL ontology graph."""
    global _ontology_graph  # noqa: PLW0603  # pylint: disable=global-statement
    if _ontology_graph is None:
        _ontology_graph = Graph()
        _ontology_graph.parse(str(ONTOLOGY_PATH), format="turtle")
    return _ontology_graph


def clear_cache() -> None:
    """Clear cached shapes and ontology graphs (useful for tests)."""
    global _shapes_graph, _ontology_graph  # noqa: PLW0603  # pylint: disable=global-statement
    _shapes_graph = None
    _ontology_graph = None


def validate_graph(
    data_graph: Graph,
    shapes_graph: Graph | None = None,
    ont_graph: Graph | None = None,
    inference: str = "rdfs",
    abort_on_first: bool = False,
) -> tuple[bool, Graph, str]:
    """
    Validate an RDF data graph against iqoqo SHACL shapes.

    Args:
        data_graph: The RDF graph to validate.
        shapes_graph: Optional custom shapes graph; defaults to cached canonical shapes.
        ont_graph: Optional custom ontology graph; defaults to cached canonical ontology.
        inference: Inferencing mode, defaults to "rdfs".
        abort_on_first: Whether to abort after first violation.

    Returns:
        Tuple of (conforms: bool, results_graph: Graph, results_text: str)
    """
    if shapes_graph is None:
        shapes_graph = _get_shapes_graph()
    if ont_graph is None:
        ont_graph = _get_ontology_graph()
    conforms, results_graph, results_text = shacl_validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ont_graph,
        inference=inference,
        abort_on_first=abort_on_first,
    )
    return conforms, results_graph, results_text


@overload
def validate_rdf_string(
    rdf_data: str,
    rdf_format: str = "turtle",
    shapes_graph: Graph | None = None,
    ont_graph: Graph | None = None,
    inference: str = "rdfs",
    return_graph: Literal[False] = False,
    **kwargs: Any,
) -> tuple[bool, str]: ...


@overload
def validate_rdf_string(
    rdf_data: str,
    rdf_format: str = "turtle",
    shapes_graph: Graph | None = None,
    ont_graph: Graph | None = None,
    inference: str = "rdfs",
    return_graph: Literal[True] = ...,
    **kwargs: Any,
) -> tuple[bool, Graph, str]: ...


def validate_rdf_string(
    rdf_data: str,
    rdf_format: str = "turtle",
    shapes_graph: Graph | None = None,
    ont_graph: Graph | None = None,
    inference: str = "rdfs",
    return_graph: bool = False,
    **kwargs: Any,
) -> tuple[bool, str] | tuple[bool, Graph, str]:
    """
    Validate an RDF string against iqoqo SHACL shapes.

    Args:
        rdf_data: The RDF data as a string.
        rdf_format: Format of the RDF data ('turtle' or 'json-ld').
        shapes_graph: Optional custom shapes graph.
        ont_graph: Optional custom ontology graph.
        inference: Inferencing mode, defaults to "rdfs".
        return_graph: If True, returns (conforms, results_graph, results_text).
            Otherwise returns (conforms, results_text).

    Returns:
        Tuple of (conforms: bool, results_text: str) or (conforms, results_graph, results_text).
    """
    fmt = kwargs.get("format", rdf_format)
    if fmt in ("jsonld", "json-ld", "application/ld+json"):
        fmt = "json-ld"
    elif fmt in ("ttl", "turtle", "text/turtle"):
        fmt = "turtle"

    data_graph = Graph()
    data_graph.parse(data=rdf_data, format=fmt)
    conforms, results_graph, results_text = validate_graph(
        data_graph,
        shapes_graph=shapes_graph,
        ont_graph=ont_graph,
        inference=inference,
    )
    if return_graph:
        return conforms, results_graph, results_text
    return conforms, results_text
