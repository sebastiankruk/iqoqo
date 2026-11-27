## Why

Production scan logs (`iqoqo-web-1`, 2026-11-26) exposed a timeout race that caused first-time book scans to drop into an empty manual entry form while a second scan of the same ISBN succeeded instantly:

1. For ISBN `9788329120463`, Google Books resolved in ~1s, but `_metadata_has_gaps()` triggered Open Library enrichment. `_make_session()` in `app/utils/isbn.py` mounts `Retry(total=3, backoff_factor=0.5)`, which applies the per-call timeout (~2.085s) per attempt across 4 attempts plus backoff sleeps (~13s), pushing `GET /api/lookup/9788329120463?format=book` to ~15s and violating the 6.0s ceiling in `book-provider-fallback-retry`.
2. The frontend scanner (`frontend/components/scanner/bottom-sheet.tsx` and `frontend/app/scan/page.tsx`) enforces a hardcoded 10s `Promise.race` timeout, which is shorter than `apiClient`'s `15_000` ms timeout in `frontend/lib/api/client.ts`. At 10s, the UI gave up and opened the empty manual form while the backend kept running and auto-saved the manifestation via `IngestService.ingest_from_meta`, so the second scan hit Postgres in under 1s.
3. For ISBN `9788327170255`, `_calc_timeout()` in `app/utils/isbn.py` passed `read_timeout=0.2` (200ms) to Biblioteka Narodowa (`katalogi.bn.org.pl`), triggering 3 `ReadTimeoutError` retries before succeeding at ~9s.

Target release: scheduled for **v1.2.0**.

## What Changes

- Enforce true wall-clock budget compliance across HTTP retries in `app/utils/isbn.py` via configurable `max_retries`, zero-retry optional gap-filling after primary resolution, a minimum viable per-provider timeout floor, and Polish Biblioteka Narodowa fallback budget reservation.
- Align frontend scanner lookup timeouts in `frontend/components/scanner/bottom-sheet.tsx` and `frontend/app/scan/page.tsx` with the shared `apiClient` timeout (`15_000` ms in `frontend/lib/api/client.ts`) and ensure clean request cancellation on timeout.

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `book-provider-fallback-retry`: Enforce wall-clock `max_duration` across HTTP retries, require zero-retry single-attempt behavior for optional secondary gap-filling, enforce a minimum viable provider timeout floor, and reserve viable timeout budget for Biblioteka Narodowa on Polish ISBN fallbacks.
- `scanner-error-fallback`: Align frontend scanner lookup timeout with the shared API client timeout (`15_000` ms) so valid in-flight lookups are not prematurely dropped into an empty manual entry form.

## Impact

- Backend: `app/utils/isbn.py`, `tests/test_isbn.py`
- Frontend: `frontend/lib/api/client.ts`, `frontend/components/scanner/bottom-sheet.tsx`, `frontend/app/scan/page.tsx`, frontend unit/E2E scanner tests
- Specs: `openspec/specs/book-provider-fallback-retry/spec.md`, `openspec/specs/scanner-error-fallback/spec.md`
