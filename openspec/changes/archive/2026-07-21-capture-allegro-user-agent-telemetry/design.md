---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

Allegro is returning `403 EDGE_REQUEST_REJECTED` and citing "incorrect user-header". To diagnose this and similar future issues, we need visibility into the exact HTTP headers (especially `User-Agent`) sent by the backend during external API requests (like cover refetches and metadata fetching).

## Goals / Non-Goals

**Goals:**

- Capture outbound HTTP request headers (like `User-Agent`, `Accept`) sent to Allegro.
- Expose these headers in OpenTelemetry spans.
- **Ensure capture reliability** by also emitting structured application logs, in case spans are dropped due to sampling or high volume.
- Redact sensitive headers like `Authorization` or `user_key`.

**Non-Goals:**

- Re-architecting the existing `requests` wrapper or OpenTelemetry instrumentation logic beyond adding attributes to spans.
- Replacing the current `User-Agent` behavior, only capturing what it is.

## Decisions

- **OpenTelemetry Span Attributes**: We will add attributes to the current span whenever we make a request to Allegro (e.g., in `app/utils/allegro.py` and `app/utils/covers.py`).
  - Keys will follow OTel semantic conventions where applicable (e.g., `http.request.header.user_agent`).
- **Structured Application Logging**: Because traces may be sampled or dropped during high-volume processing, we will also emit a structured log (e.g., `logger.info("Outbound API Request", extra={"http.request.header.user_agent": ...})`). This ensures the data is reliably ingested by OpenObserve.
- **Redaction Logic**: Any header name containing `authorization` or `key` will have its value replaced with `***REDACTED***` before being attached to the span or log.

## Risks / Trade-offs

- **Risk: Token Leakage** → Mitigation: Implement strict redaction for `Authorization`, `user_key`, etc., before passing to OpenTelemetry span attributes.
