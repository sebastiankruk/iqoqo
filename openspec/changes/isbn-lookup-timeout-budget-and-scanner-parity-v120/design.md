## Context

During production barcode scanning (`iqoqo-web-1`, 2026-11-26), initial scans of uncached books dropped into an empty manual entry form after 10 seconds, while re-scanning the same ISBN immediately returned full metadata. Log analysis showed:

1. `app/utils/isbn.py` mounts `Retry(total=3, backoff_factor=0.5)` inside `_make_session()`. Because `urllib3` applies `(connect_timeout, read_timeout)` per attempt rather than across retries, a single slow Open Library enrichment call (~2.085s timeout) expanded to ~13s across 4 attempts + backoff, pushing `GET /api/lookup/9788329120463?format=book` to ~15s despite `max_duration=6.0`.
2. `frontend/components/scanner/bottom-sheet.tsx` and `frontend/app/scan/page.tsx` wrap `apiFetch` in a hardcoded `10_000` ms `Promise.race` timeout, shorter than `apiClient`'s `15_000` ms timeout in `frontend/lib/api/client.ts`. When the 10s race fired, the UI opened the empty manual form while the backend completed at 15s and auto-saved the manifestation via `IngestService.ingest_from_meta`, making the second scan hit Postgres in under 1s.
3. For Polish ISBN `9788327170255`, `_calc_timeout()` computed `read_to = 0.2` (200ms) for Biblioteka Narodowa (`katalogi.bn.org.pl`), causing 3 `ReadTimeoutError` retries before succeeding at ~9s.

## Goals / Non-Goals

**Goals:**

- Keep `fetch_isbn_metadata` wall-clock execution strictly bounded by `max_duration` (default `6.0`s), including HTTP retries and backoff.
- Prevent optional gap-filling enrichment from stalling an already-resolved primary lookup.
- Guarantee a minimum viable timeout floor for external providers and reserve viable budget for Biblioteka Narodowa on Polish ISBNs.
- Eliminate the 10s vs 15s timeout mismatch between scanner UI components and `apiClient`.

**Non-Goals:**

- Changing the provider priority order (Google Books -> Open Library -> Biblioteka Narodowa -> Allegro).
- Modifying `IngestService.ingest_from_meta` auto-save behavior on `/api/lookup/<query>`.
- Introducing background async jobs for synchronous scanner preview lookups.

## Decisions

1. **Configurable `max_retries` on `_make_session()` and provider outcome helpers (`app/utils/isbn.py`):**
   - Update `_make_session(max_retries: int | None = None)` so `max_retries=0` mounts `HTTPAdapter(max_retries=0)` (single attempt, no `urllib3` retry/backoff loop).
   - Thread `max_retries: int | None = None` through `_lookup_google_books_outcome`, `_lookup_open_library_outcome`, `_lookup_biblioteka_narodowa_outcome`, and `_lookup_bn_primo_outcome`.
   - **Rationale:** Optional gap-filling (when Google Books already returned `SUCCESS`) should fail fast on a single attempt rather than spending 13s retrying Open Library for a cover image.

2. **Minimum viable timeout floor & Polish BN budget reservation (`app/utils/isbn.py`):**
   - Add `_MIN_ENRICHMENT_BUDGET = 1.0` and `_MIN_VIABLE_READ_TIMEOUT = 0.8` (or `1.5`s for Polish BN fallback).
   - Update `_calc_timeout(min_read: float = 0.8, max_total: float | None = None)` so `read_to` never collapses to `0.2`s; if `_remaining_time()` cannot satisfy a viable request for optional enrichment, skip enrichment and return primary metadata immediately.
   - For Polish ISBNs (`is_polish`) where Google Books returned `NO_RESULT` or `TRANSIENT_FAILURE`, cap Open Library's budget (e.g., `max_retries=0`, capped timeout <= 2.5s) so Biblioteka Narodowa (`data.bn.org.pl` / `katalogi.bn.org.pl`) always receives at least a 1.5s read timeout window.
   - **Alternative considered:** Increasing `max_duration` from `6.0`s to `12.0`s. Rejected because 12s makes scanning feel sluggish; bounding retries and reserving BN budget keeps normal scans under 6s.

3. **Shared frontend timeout constant (`frontend/lib/api/client.ts`, `bottom-sheet.tsx`, `scan/page.tsx`):**
   - Export `API_TIMEOUT_MS = 15_000` from `frontend/lib/api/client.ts` (used in `apiClient` config).
   - Replace the hardcoded `10000` ms `Promise.race` in `frontend/components/scanner/bottom-sheet.tsx` and `frontend/app/scan/page.tsx` with `API_TIMEOUT_MS` (and wire `AbortController` if `apiFetch` supports `signal`, or rely on `apiClient`'s built-in `15_000` ms timeout).
   - **Rationale:** Having a single source of truth (`API_TIMEOUT_MS`) prevents UI race timeouts from firing earlier than the HTTP client timeout.

## Risks / Trade-offs

- [Optional enrichment skipped when Open Library is slow] → Mitigation: Primary metadata (title, authors, ISBN) from Google Books is preserved immediately; missing covers can still be repaired later via AI cover repair or manual edit.
- [Waiting up to 15s on genuine network blackholes in scanner UI] → Mitigation: Backend `max_duration=6.0`s ensures normal external lookups return well under 15s, so 15s only triggers on true network/proxy stalls while eliminating false-positive timeouts.
