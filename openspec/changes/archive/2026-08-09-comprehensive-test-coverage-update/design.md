## Context

Recent updates in the `release/0.7.14` branch introduced critical security fixes, performance optimizations (Redis API caching, rate limiting), and authentication flow enhancements (InstanceSettings UI, Allegro/Twitch Auth). While security fixes (SSRF, XXE) were well-tested, significant gaps exist in caching, UI components, and authentication E2E tests. As the "Red Team" for iqoqo, we must ensure these layers adhere to the four invariant testing tiers.

## Goals / Non-Goals

**Goals:**

- Provide full backend `pytest` coverage for Redis API caching and DoS rate limiting logic.
- Add comprehensive frontend `Vitest/RTL` tests for the consolidated `InstanceSettings` component.
- Cover the Allegro device flow and Twitch API integrations with `Playwright` E2E workflows.
- Validate `load_test_facets.sh` script via `bats`.

**Non-Goals:**

- Refactoring the underlying logic for caching or authentication flows.
- Modifying non-test code outside of necessary test hooks/IDs.

## Decisions

- **Backend Cache Testing**: We will use isolated fixtures with mocked Redis connections (or local test instances) to validate `app/core/cache.py` and rate limit configurations.
- **InstanceSettings Component Testing**: Utilize `@testing-library/user-event` to simulate genuine user interactions and state changes within the massive `InstanceSettings` refactor, querying exclusively by accessible roles.
- **E2E Auth Flows**: The Playwright tests will simulate the Allegro device flow and Twitch API connections by stubbing external OAuth calls to avoid CI network timeout flakiness (similar to existing SSRF/XXE prevention).
- **Bats Coverage**: Test `load_test_facets.sh` with a `bats` script ensuring accurate parameter parsing, help menus, and graceful failure handling.

## Risks / Trade-offs

- **Risk**: External network calls in E2E tests for Allegro/Twitch may cause CI timeouts.
  - **Mitigation**: Mock external OAuth / API responses explicitly within the Playwright test setup.
- **Risk**: Testing caching logic can cause state pollution between tests.
  - **Mitigation**: Ensure strict fixture teardowns that flush the test Redis DB after every run.
