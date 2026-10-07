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
"""API-side client for the isolated SPARQL execution service."""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from flask import current_app

from app.core.sparql_service import (
    SPARQLChildProcessError,
    SPARQLConcurrencyLimit,
    SPARQLError,
    SPARQLQueryTooLarge,
    SPARQLResourceLimit,
    SPARQLSyntaxError,
    SPARQLTimeout,
    SPARQLWriteRejected,
)
from app.services.sparql.protocol import (
    ExecutionRequest,
    ProtocolErrorCode,
)

logger = logging.getLogger(__name__)


def get_sparql_service_config() -> dict[str, Any]:
    """Retrieve SPARQL execution service configuration from app or environment."""
    default_url = "http://sparql-runner:5050"
    secret = "dev-sparql-service-secret"
    enabled = True
    mode = "service"

    if current_app:
        url = current_app.config.get("SPARQL_SERVICE_URL") or os.environ.get("SPARQL_SERVICE_URL") or default_url
        secret = (
            current_app.config.get("SPARQL_SERVICE_SECRET")
            or os.environ.get("SPARQL_SERVICE_SECRET")
            or current_app.config.get("SECRET_KEY")
            or secret
        )
        enabled = current_app.config.get("SPARQL_SERVICE_ENABLED", True)
        mode = current_app.config.get("SPARQL_EXECUTION_MODE", os.environ.get("SPARQL_EXECUTION_MODE", mode))
    else:
        url = os.environ.get("SPARQL_SERVICE_URL") or default_url
        secret = os.environ.get("SPARQL_SERVICE_SECRET") or secret
        mode = os.environ.get("SPARQL_EXECUTION_MODE", mode)

    return {
        "url": url.rstrip("/"),
        "secret": secret,
        "enabled": enabled,
        "mode": mode,
    }


def execute_via_service(
    snapshot_nt: str,
    query: str,
    tenant_id: str,
    output_format: str = "application/sparql-results+json",
    deadline_seconds: float = 15.0,
    correlation_id: str | None = None,
    service_test_client: Any = None,
) -> dict[str, Any]:
    """
    Delegate SPARQL execution to the isolated execution service using signed protocol.

    Translates service errors to canonical domain exceptions.
    """
    conf = get_sparql_service_config()

    if not conf["enabled"]:
        raise SPARQLConcurrencyLimit("SPARQL execution service is currently disabled.")

    req = ExecutionRequest(
        query=query,
        snapshot=snapshot_nt,
        tenant_id=tenant_id,
        format=output_format,
        deadline_seconds=deadline_seconds,
        correlation_id=correlation_id or os.urandom(8).hex(),
    )
    req.sign(conf["secret"])
    payload = req.to_dict()

    # If an in-process test client was provided (e.g. for testing without socket networking)
    if service_test_client is not None:
        raw_res = service_test_client.post(
            "/execute",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        status_code = raw_res.status_code
        try:
            resp_data = raw_res.get_json() or {}
        except Exception:  # pylint: disable=broad-exception-caught
            resp_data = {"error": raw_res.get_data(as_text=True)}
    else:
        target_url = f"{conf['url']}/execute"
        json_bytes = json.dumps(payload).encode("utf-8")
        http_req = urllib.request.Request(
            target_url,
            data=json_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_req, timeout=deadline_seconds + 5.0) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                resp_data = json.loads(body) if body else {}
        except urllib.error.HTTPError as http_err:
            status_code = http_err.code
            try:
                body = http_err.read().decode("utf-8")
                resp_data = json.loads(body) if body else {}
            except Exception:  # pylint: disable=broad-exception-caught
                resp_data = {"error": str(http_err)}
        except (urllib.error.URLError, TimeoutError, OSError) as net_err:
            logger.error("SPARQL execution service unreachable at %s: %s", target_url, net_err)
            raise SPARQLConcurrencyLimit("SPARQL execution service is currently unavailable.") from net_err

    # Map status code and error codes
    if status_code == 200 and resp_data.get("status") == "success":
        return resp_data

    err_code = resp_data.get("error_code")
    err_msg = resp_data.get("error", "SPARQL execution failed")

    if status_code == 504 or err_code == ProtocolErrorCode.TIMEOUT:
        raise SPARQLTimeout(err_msg)
    if status_code == 413:
        if err_code == ProtocolErrorCode.QUERY_TOO_LARGE:
            raise SPARQLQueryTooLarge(err_msg)
        raise SPARQLResourceLimit(err_msg)
    if status_code == 400:
        if err_code == ProtocolErrorCode.WRITE_REJECTED:
            raise SPARQLWriteRejected(err_msg)
        if err_code == ProtocolErrorCode.SYNTAX_ERROR:
            raise SPARQLSyntaxError(err_msg)
        raise SPARQLSyntaxError(err_msg)
    if status_code in (429, 503) or err_code in (
        ProtocolErrorCode.CAPACITY_EXCEEDED,
        ProtocolErrorCode.SERVICE_UNAVAILABLE,
        ProtocolErrorCode.SERVICE_DISABLED,
    ):
        raise SPARQLConcurrencyLimit(err_msg)
    if status_code == 502 or err_code == ProtocolErrorCode.WORKER_CRASH:
        raise SPARQLChildProcessError(err_msg)

    raise SPARQLError(err_msg)
