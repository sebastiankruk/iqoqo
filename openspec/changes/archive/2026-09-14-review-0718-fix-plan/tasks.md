## 1. Batch 1: Immediate Security & Secret Protection

- [x] 1.1 Add `ALLEGRO_TOKEN_DATA`, `DISCOGS_CONSUMER_KEY`, and `DISCOGS_CONSUMER_SECRET` to `API_KEYS` in `app/api/admin.py` and verify masking via `pytest tests/test_mask_api_key.py`
- [x] 1.2 Implement rate limiting (`@limiter.limit("5 per minute")`) on `/api/admin/settings/reveal`, switch endpoint from GET to POST, and add audit log entry in `EntityAuditLog` (verify with `pytest tests/test_admin_security.py`)
- [x] 1.3 Add rate limiting (`5 per minute`) to `/api/auth/login` and `/api/auth/register` in `app/api/auth.py` and verify with `pytest tests/test_auth_security.py`
- [x] 1.4 Switch frontend auth exchange (`frontend/app/auth/exchange/route.ts`) and backend handler from GET query string to POST body and verify code exchange with `vitest run frontend/tests/auth.test.ts`
- [x] 1.5 Implement Fernet symmetric encryption helper in `app/db/settings.py` keyed from `SECRET_KEY` to encrypt all 16 secret keys and live OAuth token data on write and decrypt on read (verify with `pytest tests/test_admin_api.py`)
- [x] 1.6 Add `expires_at` column to `TokenBlocklist` in `app/db/auth.py` with periodic cleanup and use `hmac.compare_digest` for token comparisons (verify with `pytest tests/test_auth.py`)
- [x] 1.7 Delete vestigial `frontend/app/metrics/route.ts` and remove `prom-client` from `frontend/package.json` (verify build with `pnpm --prefix frontend build`)

## 2. Batch 2: Database Schema & Migration Squashing

- [x] 2.1 Consolidate 55 historical migrations in `migrations/versions/` into a single linear `v0_7_18_baseline.py` representing current canonical models
- [x] 2.2 Implement backward-compatible migration bridge in `migrations/env.py` and `run.sh` that detects revision `f65648a6aaf4` (clean 0.7.17 head) and stamps `v0_7_18_baseline` without DDL execution (verify with `flask db upgrade` on test DB)
- [x] 2.3 Extract unbatched data migrations (`20260521_backfill_work_genres.py`, `88d8fcbeb3df`, `d35f2371cfba`) into standalone CLI scripts under `scripts/migrations/` with batching and progress logging
- [x] 2.4 Move `InstanceSettings` model from `catalog` schema to `config` schema and update table references in `app/db/settings.py` (verify with `pytest tests/test_models.py`)
- [x] 2.5 Add missing `CheckConstraint` and `ondelete="SET NULL"` on optional foreign keys across `app/db/models.py` (verify with `pytest tests/test_ontology.py`)

## 3. Batch 3: Backend API Performance & Memory Limits

- [x] 3.1 Replace Python-level list slicing in `get_items()` (`app/api/items.py`) and `fetch_global_fresh_arrivals` (`app/api/facets.py`) with database-level SQL `LIMIT`/`OFFSET` and `DISTINCT ON` (verify with `pytest tests/test_api_pagination.py`)
- [x] 3.2 Add `selectinload`/`joinedload` eager fetching to `get_virtual_items` in `app/api/items.py` to eliminate N+1 query storms (verify with `pytest tests/test_api_items.py`)
- [x] 3.3 Implement Redis caching and periodic background refresh for `get_taxonomies` in `app/api/facets.py` (verify with `pytest tests/test_api_facets.py`)
- [x] 3.4 Replace sequential O(N) roadmap reordering in `app/api/collections.py` with differential SQL updates / LexoRank (verify with `pytest tests/test_api_collections.py`)
- [x] 3.5 Extract QR code SVG parsing and generation from `app/api/items.py` into dedicated `app/utils/qrcode.py` module (verify with `pytest tests/test_api_items.py`)

## 4. Batch 4: Ingestion, SSRF & External Integrations

- [x] 4.1 Fix operator precedence bug in barcode ISBN fallback heuristic in `app/strategies/default.py:30` (verify with `pytest tests/test_scanner_strategies.py`)
- [x] 4.2 Route all external cover image downloads in `app/utils/covers.py` through SSRF-safe `safe_get` (verify with `pytest tests/test_ssrf_redirect_type_safety.py`)
- [x] 4.3 Fix board game mechanics double-unwrap bug in `frontend/types/boardgame.ts` and API adapter (verify with `vitest run frontend/tests/boardgame.test.ts`)

## 5. Batch 5: Frontend Architecture & 0.8.0 Alignment

- [x] 5.1 Harmonize TanStack React Query invalidation keys across `frontend/hooks/`, `success-card.tsx`, and `add-to-collection-dropdown.tsx` to matching key tuples (verify with `vitest run frontend/tests/collection.test.tsx`)
- [x] 5.2 Prune dead uncalled `getRecentManifestations` function from `frontend/lib/api/client.ts` (verify with `pnpm --prefix frontend type-check`)
- [x] 5.3 Disable unwired "Add Child" and "Escalate/Delete" controls in `frontend/components/admin/frbr-editor.tsx` and attach "Coming in v0.8.0" tooltip (verify with `vitest run frontend/tests/frbr-editor.test.tsx`)
- [x] 5.4 Replace manual `setInterval` polling in `frontend/components/manifestation/manifestation-actions.tsx` with declarative React Query `refetchInterval` (verify with `vitest run frontend/tests/manifestation-actions.test.tsx`)
- [x] 5.5 Deduplicate select options in `frontend/components/collection/bulk-add-toolbar.tsx` (verify with `vitest run frontend/tests/bulk-add-toolbar.test.tsx`)

## 6. Batch 6: Operational Guardrails, Test Reliability & Governance Protection

- [x] 6.1 Add interactive typed confirmation prompts and production environment checks to `scripts/clone.sh`, `scripts/init_db.py --reset`, and `scripts/migrate_legacy.py --clear` (verify by executing dry-run tests in `tests/bash/`)
- [x] 6.2 Delete deprecated `scripts/allegro_auth.sh` and fix Zip Slip vulnerability in `scripts/restore_covers.py` (verify with `pytest tests/test_security_uploads.py`)
- [x] 6.3 Decouple database migrations in `docker-compose.yml` into a dedicated one-shot `migration` container service (verify compose syntax with `docker compose config`)
- [x] 6.4 Remove hardcoded `SuperSecret!123` fallback from `docker-compose.monitoring.yml` and require explicit `.env` variable (verify with `docker compose -f docker-compose.monitoring.yml config`)
- [x] 6.5 Resolve frontend test import race conditions in `frontend/tests/item-card.test.tsx` by moving `import("sonner")` to top-level module scope (verify with `pnpm --prefix frontend test`)
- [x] 6.6 Update project rules (`.agent/rules/iqoqo-standards.md`) and agent skills (`implementation-expert`, `security-auditor`, `test-craftsman`) with strict mandatory checks for secret encryption, SQL pagination, UI button wiring, and migration DAG linear heads to permanently prevent regressions
