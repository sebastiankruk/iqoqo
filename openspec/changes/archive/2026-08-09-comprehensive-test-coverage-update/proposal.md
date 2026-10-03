## Why

The `release/0.7.14` branch introduced major features including Redis API caching, DoS rate limiting, a consolidated InstanceSettings UI, and new Allegro/Twitch authentication flows. However, these features lack adequate test coverage across the backend, frontend component, E2E, and ops layers. This update addresses these gaps to ensure system stability and protect against future regressions, aligning with our strict testing invariants.

## What Changes

- **Backend**: Add pytest coverage for `app/core/cache.py` (Redis caching) and rate limiting logic.
- **Frontend**: Add Vitest/RTL component tests for the `InstanceSettings` UI which underwent massive consolidation.
- **E2E**: Add Playwright workflows for the Allegro device auth flow and Twitch API integrations.
- **Script/Ops**: Add Bats tests to validate the `load_test_facets.sh` script execution and parameter handling.

## Capabilities

### New Capabilities

- `test-coverage-caching`: Backend test suite for Redis caching and DoS rate limiting.
- `test-coverage-settings-ui`: Frontend component test suite for the InstanceSettings UI.
- `test-coverage-auth-flows`: E2E test suite for Allegro and Twitch authentication flows.
- `test-coverage-ops-scripts`: Ops test suite for load testing scripts.

### Modified Capabilities

-

## Impact

- Improves CI/CD pipeline reliability and test completeness.
- Modifies testing directories (`tests/`, `frontend/__tests__/`, `tests/bash/`).
- No production application code or APIs will be altered.
