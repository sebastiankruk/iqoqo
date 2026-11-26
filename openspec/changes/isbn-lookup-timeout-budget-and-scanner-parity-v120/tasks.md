## 1. Backend ISBN Budget & Retry Hardening

- [ ] 1.1 Update `_make_session()` in `app/utils/isbn.py` to accept `max_retries: int | None = None` and mount `HTTPAdapter(max_retries=0)` when `max_retries == 0`
- [ ] 1.2 Thread `max_retries: int | None = None` through `_lookup_google_books_outcome()`, `_lookup_open_library_outcome()`, `_lookup_biblioteka_narodowa_outcome()`, and `_lookup_bn_primo_outcome()`
- [ ] 1.3 Update `fetch_isbn_metadata()` in `app/utils/isbn.py` to use `max_retries=0` for optional secondary gap-filling, enforce a minimum viable timeout floor in `_calc_timeout()`, skip optional enrichment when remaining budget is below the viable floor, and reserve viable budget for Biblioteka Narodowa on Polish ISBNs

## 2. Backend Regression Tests

- [ ] 2.1 Add unit tests in `tests/test_isbn.py` verifying that optional Open Library gap-filling uses `max_retries=0` and does not exceed `max_duration` when Open Library times out
- [ ] 2.2 Add unit tests in `tests/test_isbn.py` verifying that sub-viable remaining budget skips optional enrichment and that Polish ISBNs (`97883` / `97983`) reserve viable read timeout budget (`>= 1.5`s) for Biblioteka Narodowa
- [ ] 2.3 Run `IQOQO_AI_MODE=1 pytest tests/test_isbn.py` and verify all tests pass

## 3. Frontend Scanner Timeout Parity

- [ ] 3.1 Export `API_TIMEOUT_MS = 15_000` from `frontend/lib/api/client.ts` and use it in `apiClient`
- [ ] 3.2 Replace the hardcoded `10000` ms `Promise.race` timeout in `frontend/components/scanner/bottom-sheet.tsx` and `frontend/app/scan/page.tsx` with `API_TIMEOUT_MS` (and wire `AbortController` / clean timeout cancellation if supported by `apiFetch`)

## 4. Frontend Unit & E2E Verification

- [ ] 4.1 Add or update Vitest unit tests covering scanner lookup timeout parity (`15_000` ms) and manual entry fallback
- [ ] 4.2 Verify `frontend/__tests__/e2e/scanner_workflow.spec.ts` passes against the updated timeout behavior

## 5. Release Hygiene (v1.2.0)

- [ ] 5.1 Run `make format-python`, `make format-js`, `IQOQO_AI_MODE=1 make lint`, `make secret-scan`, and `IQOQO_AI_MODE=1 make test-parallel`
- [ ] 5.2 Update `docs/CHANGELOG.md` under `v1.2.0`
