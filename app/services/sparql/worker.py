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
"""Killable query worker execution engine with process isolation, cgroup/rlimit bounds, and IPC."""

import contextlib
import logging
import multiprocessing
import os
import resource
import time
from typing import Any

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.plugins.sparql.parser import parseQuery

from app.core.sparql_service import (
    MAX_RESULT_ROWS,
    MAX_RESULT_TRIPLES,
    MAX_SERIALIZED_BYTES,
    classify_operation,
)
from app.services.sparql.protocol import (
    ProtocolErrorCode,
    SPARQLProtocolException,
)

logger = logging.getLogger(__name__)

# Child process execution limits (virtual address space ceiling)
CHILD_MAX_MEMORY_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB virtual address space


_MP_CONTEXT = multiprocessing.get_context("fork" if hasattr(os, "fork") else "spawn")


def _apply_process_rlimits(timeout_seconds: float) -> None:
    """Apply strict resource limits inside the isolated query child process."""
    try:
        # Prevent core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass

    try:
        # Bounded CPU time limit: give 2s buffer beyond timeout before SIGXCPU
        cpu_sec = int(timeout_seconds) + 2
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec + 1))
    except (ValueError, OSError):
        pass

    try:
        # Virtual memory (address space) ceiling
        resource.setrlimit(resource.RLIMIT_AS, (CHILD_MAX_MEMORY_BYTES, CHILD_MAX_MEMORY_BYTES))
    except (ValueError, OSError):
        pass


def _execute_in_child(
    snapshot_nt: str,
    query: str,
    output_format: str,
    timeout_seconds: float,
    conn: Any,
) -> None:
    """Isolated query worker function running in child process."""
    try:
        _apply_process_rlimits(timeout_seconds)

        # 1. Parse query and classify operation
        operation = classify_operation(query)
        parseQuery(query)

        # 2. Deserialize RDF snapshot
        graph = Graph()
        graph.parse(data=snapshot_nt, format="application/n-triples")

        # 3. Execute query
        result = graph.query(query)

        # 4. Serialize result according to requested format
        if operation == "ASK":
            is_true = bool(getattr(result, "askAnswer", False))
            if output_format == "application/sparql-results+xml":
                ser_data = result.serialize(format="xml")
                data_out: Any = ser_data.decode("utf-8") if isinstance(ser_data, bytes) else ser_data
            else:
                data_out = {"head": {}, "boolean": is_true}
            response_payload = {
                "operation": "ASK",
                "format": output_format,
                "data": data_out,
                "row_count": 1,
                "triple_count": None,
            }

        elif operation == "SELECT":
            variables = [str(v) for v in result.vars] if result.vars else []
            if output_format == "application/sparql-results+xml":
                ser_data = result.serialize(format="xml")
                data_out = ser_data.decode("utf-8") if isinstance(ser_data, bytes) else ser_data
                row_count = None
            elif output_format == "text/csv":
                ser_data = result.serialize(format="csv")
                data_out = ser_data.decode("utf-8") if isinstance(ser_data, bytes) else ser_data
                row_count = None
            elif output_format == "text/tab-separated-values":
                ser_data = result.serialize(format="tsv")
                data_out = ser_data.decode("utf-8") if isinstance(ser_data, bytes) else ser_data
                row_count = None
            else:
                # Default JSON
                bindings: list[dict[str, Any]] = []
                for row in result:
                    if len(bindings) >= MAX_RESULT_ROWS:
                        break
                    binding: dict[str, Any] = {}
                    for i, var in enumerate(variables):
                        value = row[i]  # type: ignore[index]
                        if value is not None:
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
                data_out = {
                    "head": {"vars": variables},
                    "results": {"bindings": bindings},
                }
                row_count = len(bindings)

            response_payload = {
                "operation": "SELECT",
                "format": output_format,
                "data": data_out,
                "row_count": row_count,
                "triple_count": None,
            }

        else:
            # CONSTRUCT or DESCRIBE
            res_graph = getattr(result, "graph", None) or Graph()
            triple_count = len(res_graph)
            if triple_count > MAX_RESULT_TRIPLES:
                conn.send(
                    (
                        "error",
                        ProtocolErrorCode.RESOURCE_LIMIT,
                        f"Result graph ({triple_count} triples) exceeds limit of {MAX_RESULT_TRIPLES}",
                    )
                )
                return

            if output_format == "application/ld+json":
                ser_graph = res_graph.serialize(format="json-ld", indent=2)
            elif output_format == "application/rdf+xml":
                ser_graph = res_graph.serialize(format="xml")
            else:
                ser_graph = res_graph.serialize(format="turtle")

            ser_str = ser_graph.decode("utf-8") if isinstance(ser_graph, bytes) else ser_graph
            if len(ser_str.encode("utf-8")) > MAX_SERIALIZED_BYTES:
                conn.send(
                    (
                        "error",
                        ProtocolErrorCode.RESOURCE_LIMIT,
                        f"Serialized result exceeds limit of {MAX_SERIALIZED_BYTES} bytes",
                    )
                )
                return

            response_payload = {
                "operation": operation,
                "format": output_format,
                "data": ser_str,
                "row_count": None,
                "triple_count": triple_count,
            }

        conn.send(("success", response_payload))

    except MemoryError:
        conn.send(("error", ProtocolErrorCode.RESOURCE_LIMIT, "Worker memory limit exceeded"))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        msg = str(exc)
        if "Parse" in msg or "Syntax" in msg or "Expected" in msg:
            conn.send(("error", ProtocolErrorCode.SYNTAX_ERROR, f"SPARQL syntax error: {msg}"))
        elif "Write operations" in msg:
            conn.send(("error", ProtocolErrorCode.WRITE_REJECTED, msg))
        else:
            conn.send(("error", ProtocolErrorCode.INTERNAL_ERROR, f"Query execution failed: {msg}"))
    finally:
        with contextlib.suppress(Exception):
            conn.close()


def _terminate_child(process: Any) -> None:
    """Escalating kill of child process: SIGTERM -> wait -> SIGKILL."""
    try:
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.5)
    except (OSError, ValueError):
        pass


class QueryExecutionEngine:
    """Supervises isolated query execution with killable child processes and timeouts."""

    def __init__(self) -> None:
        self.total_queries = 0
        self.total_timeouts = 0
        self.total_crashes = 0
        self.total_worker_restarts = 0

    def execute(
        self,
        snapshot_nt: str,
        query: str,
        output_format: str,
        deadline_seconds: float,
    ) -> dict[str, Any]:
        """
        Execute query in a dedicated killable child worker process.

        Raises SPARQLProtocolException on timeout, crash, or execution failure.
        """
        start_time = time.time()
        parent_conn, child_conn = _MP_CONTEXT.Pipe(duplex=False)
        process = _MP_CONTEXT.Process(
            target=_execute_in_child,
            args=(snapshot_nt, query, output_format, deadline_seconds, child_conn),
            daemon=True,
        )

        try:
            self.total_queries += 1
            process.start()
            child_conn.close()  # Close child end in parent

            # Wait for result up to deadline_seconds
            if not parent_conn.poll(deadline_seconds):
                # Timeout
                self.total_timeouts += 1
                self.total_worker_restarts += 1
                _terminate_child(process)
                raise SPARQLProtocolException(
                    ProtocolErrorCode.TIMEOUT,
                    f"SPARQL query execution exceeded {deadline_seconds}s deadline",
                )

            # Receive payload
            try:
                status, *payload = parent_conn.recv()
            except (EOFError, OSError) as e:
                self.total_crashes += 1
                self.total_worker_restarts += 1
                _terminate_child(process)
                exit_code = process.exitcode
                raise SPARQLProtocolException(
                    ProtocolErrorCode.WORKER_CRASH,
                    f"Query worker crashed or exited unexpectedly (exitcode={exit_code})",
                ) from e

            process.join(timeout=1.0)
            if process.is_alive():
                _terminate_child(process)

            if status == "error":
                err_code, err_msg = payload[0], payload[1]
                raise SPARQLProtocolException(err_code, err_msg)

            res_dict = payload[0]
            res_dict["duration_ms"] = (time.time() - start_time) * 1000.0
            return res_dict

        finally:
            with contextlib.suppress(Exception):
                parent_conn.close()
            with contextlib.suppress(Exception):
                child_conn.close()
            if process.is_alive():
                _terminate_child(process)
