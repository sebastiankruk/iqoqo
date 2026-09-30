## Why

The `/allegro/device-flow` OAuth integration has no E2E test coverage. If Allegro changes their API contract (response shapes, error codes, polling intervals), the UI polling loop could enter an infinite loop or crash silently. Playwright tests mocking the external Allegro API contract will catch regressions before they reach production.

## What Changes

- **Add Playwright E2E tests** for the `/allegro/device-flow` endpoint that mock external Allegro API responses
- **Cover** happy path (successful device code flow), error paths (API unavailable, invalid credentials), and edge cases (expired device codes, polling timeout)
- **Mock** at the network level using Playwright's `page.route()` to intercept external Allegro API calls without touching Flask internals

## Capabilities

### New Capabilities

- `allegro-e2e-contract-tests`: Playwright E2E tests mocking Allegro OAuth device flow API contract

### Modified Capabilities

- None — pure test addition, no existing specs modified

## Impact

- **Files:** New `frontend/__tests__/e2e/allegro_device_flow.spec.ts`, new test fixtures
- **Tests:** Playwright E2E test suite
- **Risk:** Low — no application code modified
- **Dependencies:** Requires E2E test infrastructure (Playwright, test DB seeded with Allegro settings)
