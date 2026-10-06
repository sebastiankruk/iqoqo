---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:48Z
---

## Why

Several Site Reliability Engineering (SRE) and security patches deferred from v0.7.11 need to be implemented to ensure deployment stability and data privacy. Specifically, malformed mapping files can currently break deployments, third-party API keys (like IGDB/Twitch `Client-ID`) are leaking into telemetry because the sanitizer is unaware of them, and race conditions during OAuth callbacks across multiple tabs can cause authentication instability.

## What Changes

- **YAML Validation CI**: Add a lightweight linter/validator step to the CI pipeline to catch syntax errors and malformed dictionaries in `shared/format_mappings.yaml` before deployment.
- **Telemetry Sanitization Expansion**: Update `sanitize_headers` in `app/core/telemetry.py` to redact `Client-ID` and other non-standard vendor authentication headers, preventing them from bleeding into OpenObserve logs and traces.
- **OAuth Concurrency Testing**: Implement a Playwright E2E test to simulate and verify the robustness of the OAuth `callbackUrl` session handling when multiple browser tabs attempt to authenticate simultaneously.

## Capabilities

### New Capabilities

- `yaml-validation`: Introduces automated pre-deployment validation for shared configuration files.
- `telemetry-sanitization`: Expands outbound HTTP telemetry redacting to cover non-standard vendor credentials.
- `oauth-concurrency`: Establishes E2E test coverage for multi-tab OAuth session race conditions.

### Modified Capabilities

None

## Impact

- **Infrastructure**: CI pipeline (Makefile or GitHub Actions workflow) will include a new YAML validation step.
- **Backend**: `app/core/telemetry.py` will have expanded dictionary keys in its `sensitive_keywords` set.
- **Testing**: New Playwright test cases added to the `frontend/__tests__/e2e/` suite.
