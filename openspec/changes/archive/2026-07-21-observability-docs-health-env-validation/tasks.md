---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Telemetry Trace Sanitization & Hook Wiring

- [x] 1.1 Update `app/core/telemetry.py` to expose helper for explicit Flask instrumentor setup with `request_hook` and `response_hook`.
- [x] 1.2 Wire telemetry hooks into application factory (`app/__init__.py` or WSGI runner) when OTel instrumentation is initialized.
- [x] 1.3 Add pytest test case to verify `Authorization` header redaction in emitted OTel spans.

## 2. OTLP Routing & Docker Compose Configuration Alignment

- [x] 2.1 Update `docker-compose.yml` environment defaults for `OTEL_EXPORTER_OTLP_ENDPOINT` to ensure correct container-to-container routing (`http://otel-collector:4318` / internal network mapping).
- [x] 2.2 Verify `docker-compose.monitoring.yml` OTel Collector port bindings and CORS origins in `deploy/otel-collector-prod.yaml` / `deploy/otel-collector-local.yaml`.
- [x] 2.3 Ensure `.env.example` includes updated OTLP endpoint standards and OpenObserve configuration keys.

## 3. Automated Health Verification & Status Script Extension

- [x] 3.1 Update `scripts/status.sh` (or Makefile target `make status`) to check OpenObserve API health (`:5080/api/health`) and OTel Collector readiness (`:8888`).
- [x] 3.2 Add warning/error reporting to `make status` if OTel exporters are active but endpoints are unreachable.

## 4. Documentation Update & Testing

- [x] 4.1 Update `docs/MONITORING.md` with complete 8-layer OTel flow, accurate port topology, RUM setup, and OpenObserve SQL diagnostic examples.
- [x] 4.2 Run `make status` and backend pytest suite to verify all checks pass.
