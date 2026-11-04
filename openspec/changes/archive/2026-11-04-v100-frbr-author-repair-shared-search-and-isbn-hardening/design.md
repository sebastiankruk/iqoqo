## Context

`C100c` introduced Allegro parameter author backfilling (`scripts/repair_frbr_authors.py`), manifestation display author fallback (`app/api/manifestations.py`), Biblioteka Narodowa ISBN lookup (`app/utils/isbn.py`), and PostgreSQL FTS parity for shared collections (`app/api/public_items.py`, `app/core/search_service.py`). Deep code review revealed critical edge cases across relational FRBR `WorkContribution` preservation, multi-status shared wishlists, hidden-item FTS pagination windows, Gunicorn worker blocking, and Docker operational safety.

## Goals / Non-Goals

**Goals:**
- Guarantee zero loss of existing non-author `WorkContribution` roles (`director`, `designer`, `artist`, `composer`, `translator`, `editor`) during catalog author repair while respecting the strict FRBR `Work -> Expression -> Manifestation -> Item` boundary.
- Ensure shared collections (`/api/public/share/<token>`) never crash on multi-status filters, never crash on SQLite, never leak or get starved by `is_hidden=True` items, and escape SQL `ILIKE` wildcards (`%`, `_`).
- Prevent synchronous Gunicorn worker starvation and root-owned container file creation during `repair-authors` maintenance.
- Keep `isbn.py` strict deadline budgets, BN outbound telemetry, and OpenAPI 3.1 route documentation 100% consistent.

**Non-Goals:**
- Altering external Biblioteka Narodowa or Allegro network response schemas.
- Introducing any Alembic database schema migrations.

## Decisions

### 1. Additive Author Contribution Repair Preserving Non-Author Roles
`FrbrService.sync_entity_contributions` is a full-replacement API intended for complete contribution lists. Passing only `[{"name": ..., "role": "author"}]` deletes all non-author `WorkContribution` rows.
- **Decision:** In `repair_work_authors()`, read existing non-author `WorkContribution` entries (`wc.role != "author"`) and preserve them intact (or only upsert missing `"author"` `WorkContribution` rows without deleting other roles). Do **not** copy `Work` authors onto `Manifestation.meta["authors"]`. Only mark a `Work` as repaired when `normalized` produces at least one valid author name that differs from current `work.meta["authors"]` or missing `"author"` `WorkContribution`s, and call `db.session.commit()` once per batch outside the inner `for work in works:` loop.

### 2. Push `include_hidden` Into `_pg_item_fts` & Normalize Shared Filter Lists
- **Decision:** Add `include_hidden: bool = True` to `ItemSearchFilters` and `SearchService.search_items(...)`. In `_pg_item_fts`, bind `:include_hidden` (`AND (:include_hidden = TRUE OR i.is_hidden = FALSE)`) inside the SQL query *before* `ORDER BY ... LIMIT :limit` so hidden items never consume public search result slots.
- Normalize `raw_statuses = filters.get("status")` (`[raw_statuses]` if `isinstance(..., str)` else list) and `raw_tags = filters.get("tags")` into `list[str]` at the top of `fetch_shared_collection_by_token`, eliminating `TypeError: unhashable type: 'list'` on `_INTENT_LEVEL_STATUSES` set intersections and single-char string tuple expansion.
- Replace legacy `db.session.query(UserWorkIntent)` + `func.immutable_unaccent` + `_meta_text(Work.meta)` with SQLAlchemy 2.0 `select(UserWorkIntent)` using dialect-aware `unaccent` (PostgreSQL only) and targeted title/author/contributor clauses escaped via `escape_ilike_term()`.

### 3. Safe Operational & HTTP Execution for `repair-authors`
- **Decision:** For `POST /api/admin/maintenance/repair-authors`, run `dry_run=True` bounded/read-only and dispatch `dry_run=False` via `submit_task` (falling back synchronously in eager/test mode) while logging an `EntityAuditLog` entry (`action="maintenance_repair_authors"`). In `Makefile`, execute `docker compose exec -T web` (default `appuser`, never `-u root`), default to `--dry-run` unless `apply=1` is passed (or require explicit `env=prod` / `prod` target rather than silently auto-mutating a detected production container), and add `repair-authors` to `.PHONY` and `help:`.

## Risks / Trade-offs

- **[Changing `make repair-authors` Default or Prod Auto-Detection]** -> Mitigation: Support `make repair-authors preview` (`--apply` on preview when explicitly targeted) and require explicit `make repair-authors prod` (with production confirmation guard unless `YES=1` / `--yes` or `dry_run=1` is passed) so an accidental bare `make repair-authors` on a production host never mutates prod unprompted.
