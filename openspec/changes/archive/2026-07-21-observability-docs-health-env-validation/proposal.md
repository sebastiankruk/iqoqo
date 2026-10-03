---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

OpenObserve telemetry collection in production setup experienced silent data ingestion failures due to OTLP port/endpoint mismatches (`4328` vs `4318`), default `none` exporter settings, unredacted authorization headers in traces, and outdated monitoring documentation. Standardizing health verification, environment variable defaults, security hooks, and documentation ensures zero blind spot observability across all 8 platform layers.

## What Changes

- **OTLP Ingestion & Network Alignment**: Fix OTLP endpoint default configurations in `docker-compose.yml` and `docker-compose.monitoring.yml` to align OTLP HTTP (4318) and gRPC (4317) routing across containers.
- **Trace Security Sanitization**: Wire `app/core/telemetry.py` request/response hooks into Flask and Celery instrumentation to sanitize `Authorization` headers and sensitive credentials from emitted spans.
- **Automated Health & Env Validation**: Extend `make status` and environment verification scripts to validate OpenObserve connectivity, OTel Collector reachability, and exporter flag coherence (`OTEL_*_EXPORTER`).
- **Observability Documentation & Examples**: Update `docs/MONITORING.md` and `.env.example` with precise port mapping topologies, SQL query examples for OpenObserve, RUM token workflow details, and ad-blocker resilience.

## Capabilities

### New Capabilities

- `observability-health-validation`: Defines requirements for automated observability health checks, OTLP endpoint reachability, telemetry header sanitization, and OpenObserve documentation accuracy.

### Modified Capabilities

- None

## Impact

- `docker-compose.yml`, `docker-compose.monitoring.yml`, `deploy/otel-collector-prod.yaml`
- `app/core/telemetry.py` and backend entry points (`app/__init__.py` / WSGI runners)
- `make status` script (`scripts/status.sh` or `Makefile`)
- `docs/MONITORING.md` and `.env.example`
