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
"""Isolated SPARQL execution service HTTP listener and queue supervisor."""

import logging
import os
import threading
import time
from typing import Any

from flask import Flask, jsonify, request

from app.services.sparql.protocol import (
    ExecutionResponse,
    ProtocolErrorCode,
    ReplayProtector,
    SPARQLProtocolException,
    get_replay_protector,
    verify_execution_request,
)
from app.services.sparql.worker import QueryExecutionEngine

logger = logging.getLogger("iqoqo.sparql_service")

# Concurrency and queue bounds
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_MAX_QUEUE_DEPTH = 16

try:
    from opentelemetry import metrics as _otel_metrics

    _meter = _otel_metrics.get_meter("iqoqo.sparql_service")
    _otel_requests_total = _meter.create_counter("sparql_service_requests_total", description="Total requests to SPARQL service")
    _otel_timeouts_total = _meter.create_counter("sparql_service_timeouts_total", description="Total timeouts in SPARQL service")
    _otel_rejections_total = _meter.create_counter("sparql_service_rejections_total", description="Total rejections in SPARQL service")
    _otel_duration_ms = _meter.create_histogram("sparql_service_duration_ms", description="Execution duration in milliseconds")
except (ImportError, AttributeError):
    _meter = None
    _otel_requests_total = None
    _otel_timeouts_total = None
    _otel_rejections_total = None
    _otel_duration_ms = None


class ServiceMetrics:
    """Thread-safe telemetry counters and gauges for the execution service."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests_total = 0
        self.successes_total = 0
        self.failures_total = 0
        self.timeouts_total = 0
        self.capacity_rejections_total = 0
        self.auth_rejections_total = 0
        self.active_queries = 0
        self.queued_requests = 0

    def to_dict(self) -> dict[str, Any]:
        with self.lock:
            return {
                "requests_total": self.requests_total,
                "successes_total": self.successes_total,
                "failures_total": self.failures_total,
                "timeouts_total": self.timeouts_total,
                "capacity_rejections_total": self.capacity_rejections_total,
                "auth_rejections_total": self.auth_rejections_total,
                "active_queries": self.active_queries,
                "queued_requests": self.queued_requests,
            }


class AdmissionController:
    """Bounded admission controller enforcing maximum concurrent queries and queue depth."""

    def __init__(
        self,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        max_queue: int = DEFAULT_MAX_QUEUE_DEPTH,
    ) -> None:
        self.max_concurrency = max_concurrency
        self.max_queue = max_queue
        self._concurrency_sem = threading.Semaphore(max_concurrency)
        self._queue_sem = threading.Semaphore(max_queue)
        self.metrics = ServiceMetrics()

    def acquire(self, timeout: float = 2.0) -> bool:
        """Attempt to enter queue and acquire execution slot within timeout."""
        with self.metrics.lock:
            if self.metrics.queued_requests >= self.max_queue:
                self.metrics.capacity_rejections_total += 1
                return False
            self.metrics.queued_requests += 1

        try:
            acquired = self._concurrency_sem.acquire(blocking=True, timeout=timeout)
            if not acquired:
                with self.metrics.lock:
                    self.metrics.capacity_rejections_total += 1
                return False
            with self.metrics.lock:
                self.metrics.active_queries += 1
            return True
        finally:
            with self.metrics.lock:
                self.metrics.queued_requests -= 1

    def release(self) -> None:
        """Release execution slot."""
        with self.metrics.lock:
            if self.metrics.active_queries > 0:
                self.metrics.active_queries -= 1
        self._concurrency_sem.release()


def create_service_app(
    secret: str | None = None,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    max_queue: int = DEFAULT_MAX_QUEUE_DEPTH,
    replay_protector: ReplayProtector | None = None,
) -> Flask:
    """Create and configure the SPARQL execution service Flask app."""
    app = Flask("iqoqo_sparql_service")

    effective_secret = secret or os.environ.get("SPARQL_SERVICE_SECRET", "dev-sparql-service-secret")
    admission = AdmissionController(max_concurrency=max_concurrency, max_queue=max_queue)
    engine = QueryExecutionEngine()
    protector = replay_protector or get_replay_protector()

    app.config["SPARQL_SERVICE_SECRET"] = effective_secret
    app.config["ADMISSION_CONTROLLER"] = admission
    app.config["EXECUTION_ENGINE"] = engine
    app.config["SERVICE_ENABLED"] = True

    @app.route("/healthz", methods=["GET"])
    def healthz() -> tuple[Any, int]:
        """Liveness check probe."""
        return jsonify({"status": "healthy", "service": "iqoqo-sparql-service"}), 200

    @app.route("/readyz", methods=["GET"])
    def readyz() -> tuple[Any, int]:
        """Readiness check probe."""
        if not app.config.get("SERVICE_ENABLED", True):
            return jsonify({"status": "unavailable", "reason": "service_disabled"}), 503

        # Check queue saturation
        metrics = admission.metrics.to_dict()
        if metrics["queued_requests"] >= max_queue:
            return jsonify({"status": "degraded", "reason": "queue_saturated"}), 503

        return jsonify({"status": "ready", "metrics": metrics}), 200

    @app.route("/metrics", methods=["GET"])
    def metrics_endpoint() -> tuple[Any, int]:
        """Telemetry metrics endpoint."""
        data = admission.metrics.to_dict()
        data.update(
            {
                "worker_restarts_total": engine.total_worker_restarts,
                "worker_crashes_total": engine.total_crashes,
            }
        )
        return jsonify(data), 200

    @app.route("/execute", methods=["POST"])
    def execute_query() -> tuple[Any, int]:
        """Execute a validated and signed SPARQL query request."""
        start_time = time.time()
        job_id = "unknown"
        correlation_id = "unknown"

        with admission.metrics.lock:
            admission.metrics.requests_total += 1
        if _otel_requests_total is not None:
            try:
                _otel_requests_total.add(1)
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        # Check if service is disabled (controlled 503 canary / rollback switch)
        if not app.config.get("SERVICE_ENABLED", True):
            err_resp = ExecutionResponse(
                status="error",
                job_id=job_id,
                correlation_id=correlation_id,
                error_code=ProtocolErrorCode.SERVICE_DISABLED,
                error_message="SPARQL execution service is currently disabled",
                http_status=503,
            )
            return jsonify(err_resp.to_dict()), 503

        # Parse JSON
        req_data = request.get_json(silent=True)
        if not req_data:
            err_resp = ExecutionResponse(
                status="error",
                job_id=job_id,
                correlation_id=correlation_id,
                error_code=ProtocolErrorCode.INVALID_REQUEST,
                error_message="Invalid JSON request payload",
                http_status=400,
            )
            return jsonify(err_resp.to_dict()), 400

        job_id = str(req_data.get("job_id", "unknown"))
        correlation_id = str(req_data.get("correlation_id", "unknown"))

        # Verify authentication, scope, expiration, replay, digests
        try:
            verified_req = verify_execution_request(
                data=req_data,
                secret=app.config["SPARQL_SERVICE_SECRET"],
                replay_protector=protector,
            )
        except SPARQLProtocolException as exc:
            with admission.metrics.lock:
                admission.metrics.failures_total += 1
                if exc.code in (
                    ProtocolErrorCode.UNAUTHORIZED,
                    ProtocolErrorCode.SCOPE_MISMATCH,
                    ProtocolErrorCode.EXPIRED,
                    ProtocolErrorCode.REPLAY_DETECTED,
                ):
                    admission.metrics.auth_rejections_total += 1

            logger.warning(
                "SPARQL request verification failed: job_id=%s, correlation_id=%s, code=%s, err=%s",
                job_id,
                correlation_id,
                exc.code,
                exc.message,
            )
            err_resp = ExecutionResponse(
                status="error",
                job_id=job_id,
                correlation_id=correlation_id,
                error_code=exc.code,
                error_message=exc.message,
                http_status=exc.http_status,
            )
            return jsonify(err_resp.to_dict()), exc.http_status

        # Bounded admission control
        slot_acquired = admission.acquire(timeout=2.0)
        if not slot_acquired:
            err_resp = ExecutionResponse(
                status="error",
                job_id=verified_req.job_id,
                correlation_id=verified_req.correlation_id,
                error_code=ProtocolErrorCode.CAPACITY_EXCEEDED,
                error_message="SPARQL execution capacity exceeded; please retry shortly",
                http_status=503,
            )
            response = jsonify(err_resp.to_dict())
            response.headers["Retry-After"] = "5"
            return response, 503

        try:
            # Execute in isolated killable query child process
            exec_res = engine.execute(
                snapshot_nt=verified_req.snapshot,
                query=verified_req.query,
                output_format=verified_req.format,
                deadline_seconds=verified_req.deadline_seconds,
            )

            duration_ms = (time.time() - start_time) * 1000.0
            with admission.metrics.lock:
                admission.metrics.successes_total += 1
            if _otel_duration_ms is not None:
                try:
                    _otel_duration_ms.record(duration_ms, {"operation": exec_res.get("operation", "SELECT")})
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

            logger.info(
                "SPARQL execution succeeded: job_id=%s, correlation_id=%s, op=%s, duration_ms=%.2f",
                verified_req.job_id,
                verified_req.correlation_id,
                exec_res.get("operation"),
                duration_ms,
            )

            success_resp = ExecutionResponse(
                status="success",
                job_id=verified_req.job_id,
                correlation_id=verified_req.correlation_id,
                operation=exec_res.get("operation", "SELECT"),
                format=exec_res.get("format", verified_req.format),
                data=exec_res.get("data"),
                duration_ms=duration_ms,
                triple_count=exec_res.get("triple_count"),
                row_count=exec_res.get("row_count"),
                http_status=200,
            )
            return jsonify(success_resp.to_dict()), 200

        except SPARQLProtocolException as exc:
            with admission.metrics.lock:
                admission.metrics.failures_total += 1
                if exc.code == ProtocolErrorCode.TIMEOUT:
                    admission.metrics.timeouts_total += 1
            if _otel_rejections_total is not None:
                try:
                    _otel_rejections_total.add(1, {"code": exc.code})
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
            if exc.code == ProtocolErrorCode.TIMEOUT and _otel_timeouts_total is not None:
                try:
                    _otel_timeouts_total.add(1)
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

            duration_ms = (time.time() - start_time) * 1000.0
            logger.warning(
                "SPARQL execution error: job_id=%s, correlation_id=%s, code=%s, duration_ms=%.2f, msg=%s",
                verified_req.job_id,
                verified_req.correlation_id,
                exc.code,
                duration_ms,
                exc.message,
            )
            err_resp = ExecutionResponse(
                status="error",
                job_id=verified_req.job_id,
                correlation_id=verified_req.correlation_id,
                error_code=exc.code,
                error_message=exc.message,
                http_status=exc.http_status,
                duration_ms=duration_ms,
            )
            return jsonify(err_resp.to_dict()), exc.http_status

        except Exception:  # pylint: disable=broad-exception-caught
            with admission.metrics.lock:

                admission.metrics.failures_total += 1

            duration_ms = (time.time() - start_time) * 1000.0
            logger.exception(
                "SPARQL execution internal error: job_id=%s, correlation_id=%s, duration_ms=%.2f",
                verified_req.job_id,
                verified_req.correlation_id,
                duration_ms,
            )
            err_resp = ExecutionResponse(
                status="error",
                job_id=verified_req.job_id,
                correlation_id=verified_req.correlation_id,
                error_code=ProtocolErrorCode.INTERNAL_ERROR,
                error_message="Internal error during SPARQL execution",
                http_status=500,
                duration_ms=duration_ms,
            )
            return jsonify(err_resp.to_dict()), 500

        finally:
            admission.release()

    return app


if __name__ == "__main__":
    # Internal listener only
    port = int(os.environ.get("SPARQL_SERVICE_PORT", "5050"))
    service_app = create_service_app()
    service_app.run(host="0.0.0.0", port=port, threaded=True)
