---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Utility Functions

- [x] 1.1 Create or update a telemetry utility function to safely extract and redact HTTP headers (e.g., redacting `Authorization`).

## 2. Instrumentation Updates

- [x] 2.1 Update `app/utils/allegro.py` to attach outbound headers (`User-Agent`, `Accept`, `Authorization`) to the active OpenTelemetry span AND emit a structured log using the redaction utility.
- [x] 2.2 Update `app/utils/covers.py` (in `download_direct_url`) to attach the Chrome-mimicking `User-Agent` header to the active OpenTelemetry span AND emit a structured log.

## 3. Testing and Validation

- [x] 3.1 Write or update unit tests to verify that headers are properly extracted and added to span attributes.
- [x] 3.2 Ensure tests verify that sensitive headers like `Authorization` are properly redacted as `***REDACTED***`.
