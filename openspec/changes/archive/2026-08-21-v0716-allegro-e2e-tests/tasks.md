## 1. Create E2E Test Infrastructure

- [x] 1.1 Create `frontend/__tests__/e2e/allegro_device_flow.spec.ts` test file
- [x] 1.2 Set up `page.route()` interceptors for Allegro API domain (`allegro.pl`)
- [x] 1.3 Create mock response fixtures for device flow initiation, token polling, and token exchange
- [x] 1.4 Ensure E2E seed script includes Allegro client_id/client_secret in settings

## 2. Write Happy Path Tests

- [x] 2.1 Test: Admin navigates to Allegro settings and initiates device flow
- [x] 2.2 Test: UI displays device code and verification URL from mocked API
- [x] 2.3 Test: After simulated polling, UI shows success confirmation

## 3. Write Error Path Tests

- [x] 3.1 Test: Allegro API returns network error → UI shows error, no polling loop
- [x] 3.2 Test: Allegro API returns 401 → UI shows authentication error
- [x] 3.3 Test: Device code expires during polling → UI shows expiration + retry option

## 4. Verification

- [x] 4.1 Run `make format-js`
- [x] 4.2 Run `make lint-js` — verify no errors
- [x] 4.3 Run `make test-e2e` — verify all new tests pass
- [x] 4.4 Verify mock fixtures accurately represent Allegro API contract shape
