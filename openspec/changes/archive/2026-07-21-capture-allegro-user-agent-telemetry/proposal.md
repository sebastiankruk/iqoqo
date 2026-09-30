---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

Allegro is returning a `403 EDGE_REQUEST_REJECTED` and complaining about an "incorrect user-header" during API communication for cover refetches and metadata ingestion. We need to capture the exact `User-Agent` and other HTTP headers sent to Allegro (and potentially other external APIs) and include them in our telemetry. This will allow the `/iqoqo-devops-sre-expert` agent and developers to easily diagnose these issues in production via OpenObserve/telemetry dashboards.

## What Changes

- Add instrumentation to capture request headers (especially `User-Agent`, `Authorization`, and `Accept`) for outbound HTTP requests made to Allegro.
- Attach these captured headers as attributes to the current OpenTelemetry span.
- Ensure sensitive information (like tokens in `Authorization`) is redacted or safely handled before attaching to telemetry.

## Capabilities

### New Capabilities

- `external-api-telemetry`: Capturing and logging HTTP request/response headers and metadata for external API integrations (like Allegro) into OpenTelemetry spans.

### Modified Capabilities

-

## Impact

- **Affected Code**: `app/utils/allegro.py`, `app/utils/covers.py` (specifically `download_direct_url`), and potentially `app/utils/isbn.py`.
- **Telemetry**: OpenTelemetry spans will now include `http.request.header.user_agent` and other relevant attributes.
- **Dependencies**: No new external dependencies required, utilizes existing `opentelemetry` integration.
