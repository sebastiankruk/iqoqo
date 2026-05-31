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
"""SPARQL query service over in-memory RDF graphs built from user collections."""

import re
import signal
from typing import Any

from rdflib import Graph
from rdflib.query import Result

from app.core.frbr_service import serialize_collection_to_rdf

# Maximum allowed query length in bytes
MAX_QUERY_LENGTH = 10240  # 10KB

# Query execution timeout in seconds
QUERY_TIMEOUT = 5

# Patterns that indicate write operations (must be rejected)
WRITE_PATTERNS = re.compile(
    r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|ADD|MOVE|COPY)\b",
    re.IGNORECASE,
)


class SPARQLError(Exception):
    """Base exception for SPARQL service errors."""


class SPARQLQueryTooLarge(SPARQLError):
    """Raised when a query exceeds the maximum allowed size."""


class SPARQLWriteRejected(SPARQLError):
    """Raised when a write operation is attempted."""


class SPARQLTimeout(SPARQLError):
    """Raised when query execution exceeds the timeout."""


class SPARQLSyntaxError(SPARQLError):
    """Raised when the query has a syntax error."""


def _timeout_handler(signum: int, frame: Any) -> None:
    raise SPARQLTimeout(f"Query execution exceeded {QUERY_TIMEOUT}s timeout")


def validate_query(query: str) -> None:
    """
    Validate a SPARQL query string for safety.

    Raises:
        SPARQLQueryTooLarge: If query exceeds MAX_QUERY_LENGTH
        SPARQLWriteRejected: If query contains write operations
    """
    if len(query.encode("utf-8")) > MAX_QUERY_LENGTH:
        raise SPARQLQueryTooLarge(f"Query exceeds maximum size of {MAX_QUERY_LENGTH} bytes")

    if WRITE_PATTERNS.search(query):
        raise SPARQLWriteRejected("Write operations (INSERT, DELETE, etc.) are not permitted")


def build_graph(items: list[Any], base_url: str) -> Graph:
    """
    Build an in-memory RDF graph from a list of collection items.

    Uses serialize_collection_to_rdf() to produce Turtle, then parses it back
    into a Graph suitable for SPARQL querying.
    """
    turtle_data = serialize_collection_to_rdf(items, base_url, output_format="turtle")
    g = Graph()
    g.parse(data=turtle_data, format="turtle")
    return g


def execute_sparql(graph: Graph, query: str) -> Result:
    """
    Execute a validated SPARQL query against an RDF graph with timeout.

    Args:
        graph: The rdflib Graph to query
        query: A validated SPARQL query string

    Returns:
        rdflib.query.Result

    Raises:
        SPARQLTimeout: If execution exceeds QUERY_TIMEOUT
        SPARQLSyntaxError: If the query has syntax errors
    """
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(QUERY_TIMEOUT)
    try:
        result = graph.query(query)
    except SPARQLTimeout:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Parse" in error_msg or "Syntax" in error_msg or "Expected" in error_msg:
            raise SPARQLSyntaxError(f"SPARQL syntax error: {error_msg}") from e
        raise SPARQLError(f"Query execution failed: {error_msg}") from e
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    return result


def format_select_results(result: Result) -> dict:
    """
    Format SELECT query results as SPARQL Results JSON.

    See: https://www.w3.org/TR/sparql11-results-json/
    """
    variables = [str(v) for v in result.vars] if result.vars else []
    bindings = []
    for row in result:
        binding = {}
        for i, var in enumerate(variables):
            value = row[i]  # type: ignore[index]  # rdflib ResultRow supports indexing
            if value is not None:
                from rdflib import BNode, Literal, URIRef

                if isinstance(value, URIRef):
                    binding[var] = {"type": "uri", "value": str(value)}
                elif isinstance(value, BNode):
                    binding[var] = {"type": "bnode", "value": str(value)}
                elif isinstance(value, Literal):
                    entry: dict[str, str] = {"type": "literal", "value": str(value)}
                    if value.datatype:
                        entry["datatype"] = str(value.datatype)
                    if value.language:
                        entry["xml:lang"] = value.language
                    binding[var] = entry
        bindings.append(binding)

    return {
        "head": {"vars": variables},
        "results": {"bindings": bindings},
    }


def format_graph_results(result: Result, output_format: str = "turtle") -> str:
    """
    Format CONSTRUCT/DESCRIBE query results as serialized RDF.
    """
    g = result.graph if hasattr(result, "graph") and result.graph is not None else Graph()
    if output_format == "json-ld":
        return g.serialize(format="json-ld", indent=4)
    return g.serialize(format="turtle")
