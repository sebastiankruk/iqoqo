## Context

See `proposal.md` — Why. The `release/1.2.0` branch passed all 16 CI workflows at commit `31cd1b5b`, but Principal Code Review surfaced edge-case DoS, mobile credential isolation, state synchronization, backfill ordering, and release-finalization gaps across the backend API, Capacitor storage layer, frontend components, and OpenSpec registry.

## Goals / Non-Goals

**Goals:**
- Prevent malformed `Item.meta["total_reading_minutes"]` strings from raising PostgreSQL `DataError` (HTTP 500) on manifestation detail/stats endpoints and block direct client overwrites of derived reading-minute totals.
- Compute accurate elapsed `avg_reading_days` across all supported media progression states (`reading`, `listening`, `watching`, `playing`, `building`).
- Guarantee strict per-server auth token isolation and async active-server resolution across mobile login, cold start, switching, and logout.
- Keep `TaxonomyEditor` location state synchronized on external updates and support `Escape` key dismissal on the contributed covers lightbox.
- Harden the author LOD backfill script against duplicate-key ordering hazards and drop its dead `--yes` CLI flag.
- Finalize `v1.2.0` release hygiene (`openspec` sync + archiving the 9 completed `v1.2.0` changes plus `C171`, while keeping `C168` open for human SVG Task `3.2` and `C170` active for `v1.3.0`, plus dating `docs/CHANGELOG.md`).

**Non-Goals:**
- Changing FRBR schema structure, adding Alembic migrations, or modifying `v1.3.0` (`C170`) RDF separation behavior.
- Adding UI or bulk migration tooling for existing legacy `total_reading_minutes` data beyond safe cast guarding.

## Decisions

### 1. Safe `total_reading_minutes` Integer Parsing & Write Protection
- **Choice:** Extract a shared helper `_safe_total_reading_minutes_expr(dialect_name: str)` in `app/api/manifestations.py` (used by both `get_manifestation()` and `_compute_manifestation_stats()`). On PostgreSQL, check `raw_val.op("~")(r"^[0-9]{1,9}$")` inside `db.case((..., db.cast(raw_val, db.Integer)), else_=None)` before `func.avg()`. On SQLite, keep numeric validation via `func.json_extract` + `func.typeof(...)` (`"integer"` or bounded `<= 9` digit-only `"text"`). In `app/api/items.py` (`_update_physical_item`), introduce a separate `_DERIVED_ITEM_META_KEYS = {"total_reading_minutes", "reading_sessions_count", "reading_sessions"}` set excluded from `allowed_meta` — **NOT** `_DISALLOWED_ITEM_META_KEYS`, because `_DISALLOWED_ITEM_META_KEYS` pops matching keys out of `item_meta` and would wipe genuine reading totals on item edits — and guard `_compute_reading_duration_summary()` / `log_reading_session()` with safe non-negative integer parsing.
- **Alternative Considered:** Application-side Python aggregation over all public items. Rejected because project rules enforce database-level aggregation (`GROUP BY`) without unbounded heap materialization.

### 2. Multi-Media `started_at` Statuses in `_compute_manifestation_stats`
- **Choice:** Define `_STARTED_READER_STATUSES = ("reading", "currently_reading", "listening", "watching", "playing", "building")` in `app/api/manifestations.py` and pass it into `ItemStatusLog.new_status.in_(_STARTED_READER_STATUSES)` inside `_compute_manifestation_stats()`.
- **Alternative Considered:** Separate duration formulas per media category. Unnecessary because `_COMPLETED_STATUSES` already spans `read`, `listened`, `watched`, `played`, `built`.

### 3. Per-Server Mobile Token Isolation (`frontend/lib/capacitor/storage.ts`)
- **Choice:** Update `getAuthToken`, `setAuthToken`, and `removeAuthToken` to resolve `const targetId = serverId ?? (await getActiveServerId());`. In `getAuthToken()`, run `await getSavedServers()` / `migrateLegacyServerStorage()` only when migrating a legacy single-server install; never fall back from a scoped active `serverId` to un-scoped `AUTH_TOKEN_KEY`, preventing legacy tokens from leaking onto another server profile. In `removeAuthToken()`, always clear `tokenKeyForServer(targetId)` and clear `AUTH_TOKEN_KEY` whenever no multi-server profiles remain (or on full logout/legacy cleanup) so stale legacy tokens never resurrect.
- **Alternative Considered:** Clearing all tokens on every server switch. Rejected because `C156` specifically preserves per-server credentials during multi-server switching.

### 4. React External Prop Sync (`TaxonomyEditor`) & Lightbox `Escape` Key
- **Choice:** Track `prevPhysicalLocation` render-time state in `frontend/components/item/taxonomy-editor.tsx` (following the codebase's `collection/page.tsx` pattern without calling `setState` inside `useEffect`, satisfying ESLint `react-hooks/set-state-in-effect`) so external `EditItemDialog` saves update `locationInput`. In `frontend/components/manifestation/manifestation-covers-gallery.tsx`, attach a `window.addEventListener("keydown", ...)` listener while `previewUrl` is non-null to close on `Escape`.
- **Alternative Considered:** Resetting via parent `key={item.physical_location}`. Kept component self-contained so every caller (`ItemSidebar`, tests) gets synced state automatically.

### 5. Author LOD Backfill Safety (`scripts/migrate_author_lod_to_contributors.py`)
- **Choice:** Delete the losing duplicate `SemanticLink` and call `session.flush()` *before* assigning `winner.entity_type = "contributor"` and `winner.entity_id = contributor.id`, matching the inline comment and preventing any future composite unique index violation. Remove the unused `--yes` parser flag while keeping mandatory `_confirm_production_execution()` checks intact.

### 6. Release Hygiene (`openspec` & `docs/CHANGELOG.md`)
- **Choice:** After implementing and verifying tasks `1`–`5`, sync delta specs into `openspec/specs/` and archive the 9 completed `v1.2.0` changes (`isbn-lookup-timeout-budget-and-scanner-parity-v120`, `preview-clone-reencrypt-key-propagation-and-tag-parity`, `mobile-multi-server-switching-v120`, `physical-item-location-tagging-v120`, `manifestation-covers-read-stats-popularity-v120`, `aws-s3-archive-backup-repair-v120`, `graph-person-lod-canonical-dedup-v120`, `c157-c158-search-facets-openapi-and-test-hardening-v120`, `author-lod-contributor-linking-and-shacl-ontology-sync`) and `C171`, while keeping `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`, Task `3.2` waiting for human SVG regeneration) and `frbr-expression-manifestation-rdf-separation-v130` (`C170`, `v1.3.0`) open/active. Replace `## [1.2.0] - TBD` with `## [1.2.0] - 2026-11-27` in `docs/CHANGELOG.md`.

## Risks / Trade-offs

- [Legacy mobile token not yet migrated before `getAuthToken()` call] -> Calling `await getSavedServers()` (which triggers idempotent `migrateLegacyServerStorage()`) before resolving un-migrated tokens ensures single-server upgrades keep working while blocking cross-server bleed.
- [`C168` Task `3.2` awaits human SVG regeneration] -> Keep `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`) open/unarchived (`7/8` tasks) instead of marking `3.2` done prematurely via `docs/images/architecture/` vs `frontend/public/images/help/` byte-parity (since neither directory has the updated `v1.2.0` SVGs yet). Archive `C168` once the human supplies regenerated SVGs.

## Migration Plan

No database schema migrations required. Deployable directly atop `v1_2_0_item_physical_location`.
