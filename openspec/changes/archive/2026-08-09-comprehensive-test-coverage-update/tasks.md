## 1. Backend Caching & Rate Limiting Test Suite

- [ ] 1.1 Create test fixtures for mocked Redis / API Cache in `tests/conftest.py` or local test module
- [ ] 1.2 Write `pytest` cases in `tests/test_cache.py` validating Redis caching TTL and connection handling
- [ ] 1.3 Write `pytest` cases for DoS rate limiting triggers in `app/api/system.py`

## 2. Frontend InstanceSettings Component Test Suite

- [ ] 2.1 Set up `Vitest/RTL` structure in `frontend/__tests__/components/admin/instance-settings.test.tsx`
- [ ] 2.2 Write test asserting the consolidated layout renders accurately using accessible locators
- [ ] 2.3 Write tests validating the Twitch credentials form inputs and mock submission flow
- [ ] 2.4 Verify Allegro auth fallback triggers render correctly within the settings UI

## 3. E2E Auth Workflows

- [ ] 3.1 Create a new Playwright test file or extend `manual_verification_integration.spec.ts` for auth flows
- [ ] 3.2 Write E2E test covering the Allegro device flow fallback fallback UI behavior
- [ ] 3.3 Write E2E test verifying Twitch API linking workflow

## 4. Ops Script Tests

- [ ] 4.1 Create `tests/bash/load_test_facets.bats`
- [ ] 4.2 Write bats test to validate `--help` and `-h` commands
- [ ] 4.3 Write bats test to enforce URL and Token parameter requirements
