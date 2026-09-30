---
type: Concept
title: design
timestamp: 2026-07-22T10:18:48Z
---

## Context

During the v0.7.11 cycle, a few operational and security edge cases were identified but deferred.

1. The `shared/format_mappings.yaml` file (used to map external provider formats to internal ones) is edited manually, and a YAML syntax error can break production deployments.
2. The `app/core/telemetry.py` module redacts standard auth headers (like `Authorization`), but third-party integrations (like IGDB/Twitch) use non-standard headers like `Client-ID` which are currently leaking into OpenObserve telemetry.
3. The OAuth callback flow has a race condition: if a user clicks "Login with Google" multiple times resulting in multiple tabs processing the OAuth callback simultaneously, session state can become corrupted or throw 500 errors.

## Goals / Non-Goals

**Goals:**

- Prevent malformed `shared/format_mappings.yaml` files from breaking the build/deployment by linting them in CI.
- Redact `Client-ID` and other vendor-specific auth headers from OpenTelemetry tracing.
- Establish an automated test to reproduce the OAuth callback race condition, providing a baseline to fix the underlying state bug in a future PR.

**Non-Goals:**

- Completely rewriting the telemetry hook architecture.
- Fixing the OAuth race condition in this specific change (this change only introduces the *test* for it, per the roadmap).
- Introducing a heavy schema validation library for YAML (a simple syntax/dictionary check is sufficient).

## Decisions

### D1: Use `yamllint` or a simple Python script for YAML validation

**Decision**: Add a lightweight `make validate-yaml` command that runs a Python script (or `yamllint` if already installed) to load `shared/format_mappings.yaml`. If it fails to parse as a valid dictionary, the Make target exits with a non-zero status.

**Rationale**: This avoids adding heavy new Node or Python dependencies. Python's built-in `yaml` module is already present in the backend virtual environment.

### D2: Expand `sensitive_keywords` set in telemetry hook

**Decision**: In `app/core/telemetry.py`, update the `sensitive_keywords` set within `sanitize_headers` to include `"client-id"`, `"client_id"`, and `"api-key"`.

**Rationale**: The current sanitizer uses a simple substring match on header keys. Expanding the set is a low-risk, one-line change that plugs the credential leak immediately.

### D3: Playwright multi-page context for concurrency testing

**Decision**: Use Playwright's `BrowserContext` to open multiple pages simultaneously in the E2E test to simulate the OAuth race condition.

**Rationale**: Playwright natively supports multiple concurrent pages sharing the same browser context (and thus the same cookie jar/session state), which perfectly models a user furiously clicking a login link in multiple tabs.

## Risks / Trade-offs

- **[Telemetry Over-redaction]** → Mitigation: Substring matching `"client-id"` might redact benign headers that happen to contain that string. This is an acceptable trade-off for security; it is better to lose a benign header than leak an API credential.
- **[Flaky Concurrency Test]** → Mitigation: Concurrency tests are notoriously flaky in CI. The test will need to be written carefully, perhaps using `Promise.all()` to fire the callback requests simultaneously, to reliably trigger the race condition without false positives.
