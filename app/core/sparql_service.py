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

import concurrent.futures
import re
import time
from typing import Any

from rdflib import Graph
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.query import Result

from app.core.frbr_service import build_collection_rdf_graph

# Maximum allowed query length in bytes
MAX_QUERY_LENGTH = 10240  # 10KB

# Query execution timeout in seconds
QUERY_TIMEOUT = 5

# Maximum allowed SELECT result rows to prevent memory explosion
MAX_RESULT_ROWS = 1000

# Patterns that indicate write operations (must be rejected)
WRITE_PATTERNS = re.compile(
    r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|ADD|MOVE|COPY|WITH)\b",
    re.IGNORECASE,
)


class SPARQLError(Exception):
    """Base exception for SPARQL service errors."""


class SPARQLQueryTooLarge(ValueError, SPARQLError):
    """Raised when a query exceeds the maximum allowed size."""


class SPARQLWriteRejected(ValueError, SPARQLError):
    """Raised when a write operation is attempted."""


class SPARQLTimeout(SPARQLError):
    """Raised when query execution exceeds the timeout."""


class SPARQLSyntaxError(ValueError, SPARQLError):
    """Raised when the query has a syntax error."""


def validate_query(query: str) -> None:
    """
    Validate a SPARQL query string for safety.

    Raises:
        SPARQLQueryTooLarge: If query exceeds MAX_QUERY_LENGTH
        SPARQLWriteRejected: If query contains write operations
        SPARQLSyntaxError: If the query has syntax errors
    """
    if not isinstance(query, str):
        raise ValueError("Query must be a string")

    if len(query.encode("utf-8")) > MAX_QUERY_LENGTH:
        raise SPARQLQueryTooLarge(f"Query exceeds maximum size of {MAX_QUERY_LENGTH} bytes")

    if WRITE_PATTERNS.search(query):
        raise SPARQLWriteRejected("Write operations (INSERT, DELETE, etc.) are not permitted")

    try:
        parseQuery(query)
    except Exception as e:
        raise SPARQLSyntaxError(f"SPARQL syntax error: {e}") from e


def build_graph(
    items: list[Any] | None = None,
    base_url: str = "http://localhost:5000",
    user_id: Any | None = None,
) -> Graph:
    """
    Build an in-memory RDF graph materialized from catalog models or provided item entities.

    Strictly scopes Item entities to public records and items owned by user_id,
    preventing unauthorized disclosure of other users' private collection records.
    """
    if items is None:
        from sqlalchemy import or_, select
        from sqlalchemy.orm import selectinload

        from app.db.models import Expression, Item, Manifestation, Work, db

        item_stmt = select(Item).options(
            selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work)
        )
        if user_id is not None:
            item_stmt = item_stmt.where(or_(Item.is_hidden.is_(False), Item.owner_id == user_id))
        else:
            item_stmt = item_stmt.where(Item.is_hidden.is_(False))
        db_items = list(db.session.execute(item_stmt).scalars().all())

        from typing import cast

        work_stmt = select(Work).options(selectinload(cast(Any, Work.expressions)).selectinload(cast(Any, Expression.manifestations)))
        db_works = list(db.session.execute(work_stmt).scalars().all())
        entities_to_serialize: list[Any] = list(db_works) + list(db_items)
    else:
        entities_to_serialize = []
        for it in items:
            if isinstance(it, dict):
                is_hidden = it.get("is_hidden")
                is_public = it.get("is_public", not is_hidden if is_hidden is not None else True)
                owner = it.get("owner_id")
                if owner is not None and not is_public:
                    if user_id is None or str(owner) != str(user_id):
                        continue
            elif hasattr(it, "owner_id"):
                is_hidden = getattr(it, "is_hidden", False)
                is_public = getattr(it, "is_public", not is_hidden)
                owner = getattr(it, "owner_id", None)
                if owner is not None and not is_public:
                    if user_id is None or str(owner) != str(user_id):
                        continue
            entities_to_serialize.append(it)

    return build_collection_rdf_graph(entities_to_serialize, base_url)


def execute_sparql(graph: Graph, query: str, timeout: float = QUERY_TIMEOUT) -> Result:
    """
    Execute a validated SPARQL query against an RDF graph with timeout.

    Args:
        graph: The rdflib Graph to query
        query: A validated SPARQL query string
        timeout: Maximum seconds before timeout (default: 5)

    Returns:
        rdflib.query.Result

    Raises:
        SPARQLTimeout: If execution exceeds QUERY_TIMEOUT
        SPARQLSyntaxError: If the query has syntax errors
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(graph.query, query)
    try:
        result = future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as e:
        executor.shutdown(wait=False, cancel_futures=True)
        raise SPARQLTimeout(f"Query execution exceeded {timeout}s timeout") from e
    except Exception as e:
        error_msg = str(e)
        if "Parse" in error_msg or "Syntax" in error_msg or "Expected" in error_msg:
            raise SPARQLSyntaxError(f"SPARQL syntax error: {error_msg}") from e
        raise SPARQLError(f"Query execution failed: {error_msg}") from e
    finally:
        executor.shutdown(wait=False)
    return result


def format_select_results(result: Result, max_rows: int = MAX_RESULT_ROWS) -> dict[str, Any]:
    """
    Format SELECT query results as SPARQL Results JSON with safety row limits.

    See: https://www.w3.org/TR/sparql11-results-json/
    """
    if result.type == "ASK" or getattr(result, "askAnswer", None) is not None:
        return {
            "head": {},
            "boolean": bool(result.askAnswer),
        }

    variables = [str(v) for v in result.vars] if result.vars else []
    bindings: list[dict[str, Any]] = []
    start_time = time.time()

    for row in result:
        if len(bindings) >= max_rows:
            break
        if time.time() - start_time > QUERY_TIMEOUT:
            raise SPARQLTimeout(f"Query execution exceeded {QUERY_TIMEOUT}s timeout")

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
