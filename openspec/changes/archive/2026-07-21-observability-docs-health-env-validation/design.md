---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

In production environments, OpenObserve and the OTel Collector run via `docker-compose.monitoring.yml` (dynamically included by `run.sh` or composed manually). However, SRE audit (`ses_07a9`) revealed:

1. `docker-compose.yml` set `OTEL_EXPORTER_OTLP_ENDPOINT` default to `http://host.docker.internal:4318`, while the OTel collector container host port was bound to `4328` or host networking was mismatched across environments.
2. `app/core/telemetry.py` request/response hooks (which redact `Authorization` headers) were dead code because Flask auto-instrumentation via `opentelemetry-instrument` was used without custom hooks.
3. `make status` checked PostgreSQL, Redis, Celery, Nginx, and API health, but did not verify OpenObserve API status, container ingestion health, or OTel exporter configuration coherence.
4. `docs/MONITORING.md` lacked operational detail on OpenObserve SQL querying, actual port mappings across Docker environments, and validation procedures.

## Goals / Non-Goals

**Goals:**

- Fix container network OTLP endpoint routing so OTel signals (traces, metrics, logs) reach the OTel Collector on port 4318 cleanly.
- Wire `request_hook` and `response_hook` into Flask/Celery initialization to guarantee trace sanitization of `Authorization` tokens.
- Add OpenObserve & OTel Collector health checks to `scripts/status.sh` / `make status`.
- Update `docs/MONITORING.md` and `.env.example` with exact port topologies, SQL query templates, and diagnostic procedures.

**Non-Goals:**

- Replacing OpenObserve or OTel Collector with alternative observability backends (Prometheus, Jaeger, etc.).
- Modifying business domain models or FRBR schema.

## Decisions

### Decision 1: Flask / Celery Telemetry Hook Integration

- **Choice**: Explicitly wire `request_hook` and `response_hook` in application setup (`app/core/telemetry.py` / `app/__init__.py`) using `FlaskInstrumentor().instrument_app(app, request_hook=request_hook, response_hook=response_hook)` when `OTEL_TRACES_EXPORTER` is active.
- **Rationale**: Ensures token redaction works both under standard gunicorn/flask execution and when run with `opentelemetry-instrument`.
- **Alternative Considered**: Relying purely on environment variables (which OTel Python SDK does not support for custom request/response redaction hooks).

### Decision 2: OTLP Container Endpoint Standard

- **Choice**: Standardize `OTEL_EXPORTER_OTLP_ENDPOINT` inside docker-compose stacks to target `http://otel-collector:4318` when services share the internal docker network, with fallback `http://host.docker.internal:4318` for host-mode workers.
- **Rationale**: Direct container-to-container routing over the Docker bridge network eliminates host port binding dependency (`4328` vs `4318`).
- **Alternative Considered**: Binding OTel collector to host port 4318 on all nodes (can conflict with local host services).

### Decision 3: Extended Health Check in `scripts/status.sh`

- **Choice**: Include an optional monitoring check section in `scripts/status.sh` that checks OpenObserve API (`:5080/api/health`) and OTel Collector metrics endpoint (`:8888`).
- **Rationale**: Gives SRE instant visibility during `make status` into whether monitoring container endpoints are reachable and ingesting data.

## Risks / Trade-offs

- **[Risk]** Redacting authorization headers could obscure debugging token types during development. → **Mitigation**: Redact only the secret credential string (e.g. `Bearer [REDACTED]`), keeping auth scheme type visible.
- **[Risk]** Strict internal container OTLP endpoint might break legacy local dev workflows outside Docker. → **Mitigation**: Maintain fallback to `http://localhost:4318` in local `run.sh` dev environment.

## Migration Plan

1. Update `app/core/telemetry.py` to register custom hooks during Flask app creation.
2. Update `docker-compose.yml` and `docker-compose.monitoring.yml` OTLP endpoint defaults.
3. Update `scripts/status.sh` to include OpenObserve health checks.
4. Update `docs/MONITORING.md` and `.env.example`.
5. Run python unit tests and `make status` to verify validation passes.
