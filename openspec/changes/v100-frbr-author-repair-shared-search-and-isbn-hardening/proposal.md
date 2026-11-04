## Why

Principal review of `v1.0.0` (PR #392) uncovered two `CRITICAL` backend/data-integrity defects and six `MODERATE`/`LOW` domain, search, operational, and contract issues:
1. **Destructive Relational Contributor Wipe (`scripts/repair_frbr_authors.py`):** `repair_work_authors()` invokes `FrbrService.sync_entity_contributions(work, [{"name": name, "role": "author"} ...])`, which deletes every existing `WorkContribution` row whose `(contributor_id, role)` is not in the passed list — permanently wiping `director`, `designer`, `artist`, `composer`, `translator`, and `editor` roles! It also copies Work-level authors into `Manifestation.meta["authors"]` (violating FRBR boundaries), commits mid-loop expiring SQLAlchemy batch attributes, and repeatedly flags empty-author works on every `--dry-run`.
2. **Shared Collection `500 TypeError`, SQLite Crash & Hidden-Item FTS Exhaustion (`app/api/public_items.py`, `app/core/search_service.py`):** Multi-status shared views store `filters["status"]` as `list[str]`, causing `status_val in _INTENT_LEVEL_STATUSES` (`set`) to crash with `TypeError: unhashable type: 'list'`; wishlist search unconditionally calls PostgreSQL-only `func.immutable_unaccent` and full-JSON `_meta_text(Work.meta)` via legacy `db.session.query()`; `_pg_item_fts` omits `i.is_hidden = FALSE`, allowing 50 hidden items to starve public shared search results; and `build_ilike_search_clause` omits `escape_ilike_term()`.
3. **FRBR Display Fallback, Sync Admin Repair, ISBN Timeouts & OpenAPI Drift:** `_resolve_manifestation_display_author` (`app/api/manifestations.py`) misses relational `Work.contributions` / `Expression.contributions` and lacks `getattr(m, "author", None)` duck-typing; `POST /api/admin/maintenance/repair-authors` blocks Gunicorn workers synchronously without audit logging while `Makefile` `repair-authors` runs as `-u root` and defaults to `--apply` against auto-detected production; `app/utils/isbn.py` has duplicate unreachable lines, a 1.5s connect floor breaching `max_duration`, and missing BN telemetry; `app/config.py` / `.env.example` have duplicate keys; and `app/api/docs.py` misreports `200` JSON on `302` Apple OAuth routes.

## What Changes

- **Non-Destructive, FRBR-Pure Author Repair & Display (`scripts/repair_frbr_authors.py`, `app/api/manifestations.py`, `app/api/admin.py`, `Makefile`):**
  - Preserve all non-author `WorkContribution` roles (`director`, `designer`, `artist`, `composer`, `translator`, `editor`) and sequences during author repair; stop copying Work authors onto `Manifestation.meta["authors"]`; skip unrepairable empty-author works so `--dry-run` is idempotent; and commit once per batch.
  - Fall back to relational `Work.contributions` / `Expression.contributions` and `getattr(m, "author", None)` in `_resolve_manifestation_display_author`.
  - Dispatch non-dry-run `POST /api/admin/maintenance/repair-authors` via `submit_task` (or bounded batch execution) with `EntityAuditLog` tracking; update `Makefile` `repair-authors` to run as default container `appuser` (never `-u root`), require explicit confirmation/env before mutating production, and register in `.PHONY` + `help:`.
- **Shared Collection & FTS Search Hardening (`app/api/public_items.py`, `app/core/search_service.py`):**
  - Add `include_hidden: bool = True` to `ItemSearchFilters` / `SearchService.search_items` (passing `include_hidden=False` from `public_items.py` directly into `_pg_item_fts` SQL before `LIMIT`).
  - Normalize `filters["status"]` and `filters["tags"]` to `list[str]` safely in `public_items.py`, migrate wishlist intent queries to SQLAlchemy 2.0 `select(UserWorkIntent)` with dialect-safe field-scoped `ILike` clauses, and apply `escape_ilike_term()` (`escape="\\"`) in `build_ilike_search_clause`.
- **ISBN Resilience, Config Hygiene & OpenAPI 3.1 Accuracy (`app/utils/isbn.py`, `app/services/sparql/worker.py`, `app/config.py`, `.env.example`, `app/api/docs.py`):**
  - Clamp `_calc_timeout()` connect timeout to `remaining`, emit `record_outbound_telemetry("biblioteka_narodowa", ...)`, and delete unreachable duplicate return lines in `app/utils/isbn.py`.
  - Narrow exception catching in `app/services/sparql/worker.py`, deduplicate `FEDERATION_ENABLED` (`app/config.py`) and `ALLOW_LLM` (`.env.example`), document `NEXT_PUBLIC_INSTANCE_URL`, and annotate accurate `302` / request schemas for Apple OAuth, `/api/auth/exchange`, and `repair-authors` in `app/api/docs.py`.

## Capabilities

### New Capabilities
- `frbr-author-repair-and-shared-search`: Non-destructive FRBR contributor repair, relational contributor display fallback, hidden-aware PostgreSQL FTS shared collection search, dialect-safe multi-status wishlist filtering, ISBN timeout/telemetry parity, and OpenAPI 3.1 contract alignment.

### Modified Capabilities
- None.

## Impact

- **Backend & Scripts:** `scripts/repair_frbr_authors.py`, `app/api/manifestations.py`, `app/api/admin.py`, `app/api/public_items.py`, `app/core/search_service.py`, `app/utils/isbn.py`, `app/services/sparql/worker.py`, `app/config.py`, `app/api/docs.py`, `Makefile`, `.env.example`
- **Tests:** `tests/test_frbr_author_normalization.py`, `tests/test_api_public_extended.py`, `tests/test_api_admin.py`, `tests/test_isbn.py`, `tests/test_openapi_contract_completeness.py`
