## Context

The Allegro OAuth device flow integration at `/allegro/device-flow` has no E2E test coverage. This endpoint initiates a device authorization flow with external Allegro APIs, and the frontend polls for completion. Contract changes from Allegro could cause UI polling loops or silent failures.

## Goals / Non-Goals

**Goals:**

- Add Playwright E2E tests covering the Allegro device flow happy path and error scenarios
- Mock external Allegro API responses at the network level using `page.route()`
- Cover edge cases: expired device codes, polling timeout, invalid credentials
- Ensure tests run in CI without external Allegro API access

**Non-Goals:**

- Modifying the Allegro OAuth implementation
- Testing Allegro's actual API (external service testing)
- Adding unit tests for Flask route handlers (covered by pytest)

## Decisions

### Decision 1: Network-level mocking with `page.route()`
**Choice:** Use Playwright's `page.route()` to intercept all requests to Allegro's API domain and return mock responses.
**Rationale:** Tests the full stack (frontend polling → Flask proxy → mock response) without external dependencies.
**Alternative considered:** MSW (Mock Service Worker) — rejected because Playwright's built-in routing is simpler and doesn't require additional dependencies.

### Decision 2: Test file location
**Choice:** `frontend/__tests__/e2e/allegro_device_flow.spec.ts`
**Rationale:** Follows existing E2E test naming convention (e.g., `ux_hotfixes_0715.spec.ts`).

## Risks / Trade-offs

- **Risk:** Mock responses may drift from actual Allegro API contract → **Mitigation:** Document mock response shapes in test fixtures with version comments
- **Risk:** Device flow requires Allegro settings pre-configured in test DB → **Mitigation:** Seed Allegro client_id/client_secret in E2E seed script
