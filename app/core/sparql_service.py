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
"""SPARQL query service with resource isolation and killable execution boundary."""

import logging
import multiprocessing
import threading
import time
from typing import Any

from rdflib import Graph
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.query import Result

from app.core.frbr_service import build_collection_rdf_graph

logger = logging.getLogger(__name__)

# Maximum allowed query length in bytes
MAX_QUERY_LENGTH = 10240  # 10KB

# Query execution timeout in seconds
QUERY_TIMEOUT = 5

# Maximum allowed SELECT result rows to prevent memory explosion
MAX_RESULT_ROWS = 1000

# Maximum number of items to materialize into graph
MAX_GRAPH_ITEMS = 5000

# Maximum number of triples in materialized graph
MAX_GRAPH_TRIPLES = 100000

# Maximum concurrent expensive queries
MAX_CONCURRENT_QUERIES = 4

# Semaphore for bounded concurrency
_query_semaphore = threading.Semaphore(MAX_CONCURRENT_QUERIES)


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


class SPARQLResourceLimit(SPARQLError):
    """Raised when resource limits are exceeded."""


class SPARQLConcurrencyLimit(SPARQLError):
    """Raised when concurrent query limit is exceeded."""


def classify_operation(query: str) -> str:
    """
    Classify a SPARQL query into its operation type using parsed algebra.

    Returns one of: 'SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE', 'UPDATE'

    Raises:
        SPARQLSyntaxError: If the query cannot be parsed
        SPARQLWriteRejected: If the query is an update operation
    """
    try:
        parsed = parseQuery(query)
        algebra = translateQuery(parsed)

        # Get the query type from the algebra
        query_type = algebra.algebra.name if hasattr(algebra.algebra, "name") else None

        if query_type in ("SelectQuery", "Select"):
            return "SELECT"
        elif query_type in ("AskQuery", "Ask"):
            return "ASK"
        elif query_type in ("ConstructQuery", "Construct"):
            return "CONSTRUCT"
        elif query_type in ("DescribeQuery", "Describe"):
            return "DESCRIBE"
        elif query_type in ("Update", "Insert", "Delete", "Load", "Clear", "Drop", "Create", "Add", "Move", "Copy"):
            raise SPARQLWriteRejected("Write operations (INSERT, DELETE, etc.) are not permitted")
        else:
            # Fallback: check for update keywords in a more sophisticated way
            # This handles edge cases where the parser might not classify correctly
            return _fallback_classify(query)
    except SPARQLWriteRejected:
        raise
    except Exception:
        # If parsing fails, try fallback classification
        return _fallback_classify(query)


def _fallback_classify(query: str) -> str:
    """
    Fallback classification using stripped query analysis.
    Removes comments and string literals before checking for update keywords.
    """
    import re

    # Remove comments (lines starting with #)
    query_no_comments = re.sub(r"#[^\n]*", "", query)

    # Remove string literals (both single and double quoted, including escaped quotes)
    query_no_literals = re.sub(r'"(?:[^"\\]|\\.)*"', '""', query_no_comments)
    query_no_literals = re.sub(r"'(?:[^'\\]|\\.)*'", "''", query_no_literals)

    # Now check for update keywords at the start of the query (case-insensitive)
    query_stripped = query_no_literals.strip().upper()

    update_keywords = ["INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "CREATE", "ADD", "MOVE", "COPY", "WITH"]
    for keyword in update_keywords:
        if query_stripped.startswith(keyword):
            raise SPARQLWriteRejected("Write operations (INSERT, DELETE, etc.) are not permitted")

    # Check for read operations
    if query_stripped.startswith("SELECT"):
        return "SELECT"
    elif query_stripped.startswith("ASK"):
        return "ASK"
    elif query_stripped.startswith("CONSTRUCT"):
        return "CONSTRUCT"
    elif query_stripped.startswith("DESCRIBE"):
        return "DESCRIBE"

    # If we can't classify, assume it's a read operation (SELECT-like)
    # The parser will catch actual syntax errors
    return "SELECT"


def validate_query(query: str) -> str:
    """
    Validate a SPARQL query string for safety and classify its operation type.

    Raises:
        SPARQLQueryTooLarge: If query exceeds MAX_QUERY_LENGTH
        SPARQLWriteRejected: If query contains write operations
        SPARQLSyntaxError: If the query has syntax errors

    Returns:
        str: The operation type ('SELECT', 'ASK', 'CONSTRUCT', 'DESCRIBE')
    """
    if not isinstance(query, str):
        raise ValueError("Query must be a string")

    if len(query.encode("utf-8")) > MAX_QUERY_LENGTH:
        raise SPARQLQueryTooLarge(f"Query exceeds maximum size of {MAX_QUERY_LENGTH} bytes")

    # Classify operation (this also checks for write operations)
    operation = classify_operation(query)

    # Try to parse to catch syntax errors early
    try:
        parseQuery(query)
    except Exception as e:
        raise SPARQLSyntaxError(f"SPARQL syntax error: {e}") from e

    return operation


def _execute_query_in_process(graph_data: bytes, query: str, result_queue: multiprocessing.Queue) -> None:
    """
    Execute a SPARQL query in a separate process.

    This function runs in a child process and can be killed if it exceeds the timeout.
    """
    try:
        # Deserialize the graph in the child process
        graph = Graph()
        graph.parse(data=graph_data, format="application/n-triples")

        # Execute the query
        result = graph.query(query)

        # Serialize the result for transfer back to parent
        if result.type == "ASK":
            result_data = {"type": "ASK", "askAnswer": bool(result.askAnswer)}
        elif result.type in ("SELECT",):
            # Serialize SELECT results
            variables = [str(v) for v in result.vars] if result.vars else []
            bindings = []
            for row in result:
                binding = {}
                for i, var in enumerate(variables):
                    value = row[i]
                    if value is not None:
                        from rdflib import BNode, Literal, URIRef

                        if isinstance(value, URIRef):
                            binding[var] = {"type": "uri", "value": str(value)}
                        elif isinstance(value, BNode):
                            binding[var] = {"type": "bnode", "value": str(value)}
                        elif isinstance(value, Literal):
                            entry = {"type": "literal", "value": str(value)}
                            if value.datatype:
                                entry["datatype"] = str(value.datatype)
                            if value.language:
                                entry["xml:lang"] = value.language
                            binding[var] = entry
                bindings.append(binding)
            result_data = {"type": "SELECT", "variables": variables, "bindings": bindings}
        else:
            # CONSTRUCT/DESCRIBE - serialize graph
            result_graph = result.graph if hasattr(result, "graph") and result.graph is not None else Graph()
            result_data = {"type": "GRAPH", "data": result_graph.serialize(format="nt")}

        result_queue.put(("success", result_data))
    except Exception as e:
        result_queue.put(("error", str(e)))


def execute_sparql(graph: Graph, query: str, timeout: float = QUERY_TIMEOUT) -> Result:
    """
    Execute a validated SPARQL query against an RDF graph with killable timeout.

    Uses a separate process that can be terminated if it exceeds the timeout,
    ensuring no unbounded work continues in the serving process.

    Args:
        graph: The rdflib Graph to query
        query: A validated SPARQL query string
        timeout: Maximum seconds before timeout (default: 5)

    Returns:
        rdflib.query.Result

    Raises:
        SPARQLTimeout: If execution exceeds timeout
        SPARQLSyntaxError: If the query has syntax errors
        SPARQLResourceLimit: If resource limits are exceeded
    """
    start_time = time.time()

    # Check concurrency limit
    if not _query_semaphore.acquire(blocking=False):
        raise SPARQLConcurrencyLimit("Too many concurrent queries. Please retry later.")

    try:
        # Serialize graph for transfer to child process
        graph_data = graph.serialize(format="nt")

        # Create result queue and child process
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_execute_query_in_process, args=(graph_data, query, result_queue), daemon=True)

        process.start()
        process.join(timeout=timeout)

        if process.is_alive():
            # Timeout exceeded - kill the process
            logger.warning("SPARQL query exceeded timeout, terminating process")
            process.terminate()
            process.join(timeout=1.0)
            if process.is_alive():
                process.kill()
                process.join()
            raise SPARQLTimeout(f"Query execution exceeded {timeout}s timeout")

        # Get result from queue
        if result_queue.empty():
            raise SPARQLError("Query execution failed: no result returned")

        status, result_data = result_queue.get()

        if status == "error":
            error_msg = result_data
            if "Parse" in error_msg or "Syntax" in error_msg or "Expected" in error_msg:
                raise SPARQLSyntaxError(f"SPARQL syntax error: {error_msg}")
            raise SPARQLError(f"Query execution failed: {error_msg}")

        # Reconstruct Result object from serialized data
        duration = time.time() - start_time
        logger.info(f"SPARQL query completed in {duration:.3f}s, type={result_data.get('type')}")

        return _reconstruct_result(result_data)

    finally:
        _query_semaphore.release()


def _reconstruct_result(result_data: dict) -> Result:
    """Reconstruct an rdflib Result object from serialized data."""
    from rdflib import BNode, Literal, URIRef

    result_type = result_data["type"]

    if result_type == "ASK":
        # Create a mock Result for ASK queries
        result = Result("ASK")
        result.askAnswer = result_data["askAnswer"]
        return result

    elif result_type == "SELECT":
        # Create a mock Result for SELECT queries
        result = Result("SELECT")
        result.vars = result_data["variables"]

        # Create bindings as a list of ResultRow objects
        bindings = []
        for binding in result_data["bindings"]:
            row_values = []
            row_dict = {}
            for var in result.vars:
                if var in binding:
                    val_data = binding[var]
                    if val_data["type"] == "uri":
                        value = URIRef(val_data["value"])
                    elif val_data["type"] == "bnode":
                        value = BNode(val_data["value"])
                    elif val_data["type"] == "literal":
                        datatype = val_data.get("datatype")
                        language = val_data.get("xml:lang")
                        value = Literal(val_data["value"], datatype=datatype, lang=language)
                    else:
                        value = None
                    row_values.append(value)
                    row_dict[var] = value
                else:
                    row_values.append(None)
                    row_dict[var] = None
            # For serialization compatibility, use plain dicts
            bindings.append(row_dict)

        result.bindings = bindings
        return result

    elif result_type == "GRAPH":
        # Create a mock Result for CONSTRUCT/DESCRIBE queries
        result = Result("CONSTRUCT")
        result.graph = Graph()
        result.graph.parse(data=result_data["data"], format="nt")
        return result

    raise SPARQLError(f"Unknown result type: {result_type}")


def build_graph(
    items: list[Any] | None = None,
    base_url: str = "http://localhost:5000",
    user_id: Any | None = None,
) -> Graph:
    """
    Build an in-memory RDF graph materialized from catalog models or provided item entities.

    Strictly scopes Item entities to public records and items owned by user_id,
    preventing unauthorized disclosure of other users' private collection records.

    Enforces resource limits on graph size to prevent memory exhaustion.
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

        # Apply item count limit
        item_stmt = item_stmt.limit(MAX_GRAPH_ITEMS)

        db_items = list(db.session.execute(item_stmt).scalars().all())

        if len(db_items) >= MAX_GRAPH_ITEMS:
            logger.warning(f"Item count reached limit of {MAX_GRAPH_ITEMS}")

        from typing import cast

        work_stmt = select(Work).options(selectinload(cast(Any, Work.expressions)).selectinload(cast(Any, Expression.manifestations)))
        db_works = list(db.session.execute(work_stmt).scalars().all())
        entities_to_serialize: list[Any] = list(db_works) + list(db_items)
    else:
        # Apply item count limit to provided items
        if len(items) > MAX_GRAPH_ITEMS:
            logger.warning(f"Provided items ({len(items)}) exceeded limit, truncating to {MAX_GRAPH_ITEMS}")
            items = items[:MAX_GRAPH_ITEMS]

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

    graph = build_collection_rdf_graph(entities_to_serialize, base_url)

    # Check triple count limit
    triple_count = len(graph)
    if triple_count > MAX_GRAPH_TRIPLES:
        raise SPARQLResourceLimit(
            f"Graph size ({triple_count} triples) exceeds limit of {MAX_GRAPH_TRIPLES}. "
            "Please reduce your collection size or contact support."
        )

    return graph


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

    # Handle both real rdflib results and our reconstructed results
    if hasattr(result, "bindings"):
        # Reconstructed result from process execution (bindings are dicts)
        for row in result.bindings[:max_rows]:
            binding = {}
            for var in variables:
                value = row.get(var)
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
    else:
        # Real rdflib result
        start_time = time.time()
        for row in result:
            if len(bindings) >= max_rows:
                break
            if time.time() - start_time > QUERY_TIMEOUT:
                raise SPARQLTimeout(f"Query execution exceeded {QUERY_TIMEOUT}s timeout")

            binding = {}
            for i, var in enumerate(variables):
                value = row[i]  # type: ignore[index]
                if value is not None:
                    from rdflib import BNode, Literal, URIRef

                    if isinstance(value, URIRef):
                        binding[var] = {"type": "uri", "value": str(value)}
                    elif isinstance(value, BNode):
                        binding[var] = {"type": "bnode", "value": str(value)}
                    elif isinstance(value, Literal):
                        entry = {"type": "literal", "value": str(value)}
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
