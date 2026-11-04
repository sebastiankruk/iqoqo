# frbr-author-repair-and-shared-search Specification

## Purpose
Ensure FRBR ontological purity and relational role preservation during author repair, resilient multi-status and hidden-aware shared collection search, bounded ISBN provider timeouts and telemetry, safe Docker/HTTP maintenance execution, and accurate OpenAPI 3.1 endpoint contracts.

## Requirements

### Requirement: Non-Destructive FRBR Author Repair & Relational Display Fallback

`scripts/repair_frbr_authors.py` SHALL preserve all non-author `WorkContribution` roles (`director`, `designer`, `artist`, `composer`, `translator`, `editor`) when repairing `Work` authors, SHALL NOT copy Work-level authors into `Manifestation.meta["authors"]`, SHALL commit once per batch rather than mid-iteration, and SHALL be idempotent on works with no recoverable authors. `_resolve_manifestation_display_author` (`app/api/manifestations.py`) SHALL fall back to relational `Work.contributions` and `Expression.contributions` before manifestation parameter fallbacks.

#### Scenario: Repairing Work author preserves existing director and translator roles
- **GIVEN** a `Work` with an existing `WorkContribution(role="translator", contributor="Maria Skibniewska")` and corrupted `work.meta["authors"] = ["Tolkien, J.R.R.; "]`
- **WHEN** `repair_work_authors(dry_run=False)` executes
- **THEN** `"J.R.R. Tolkien"` is normalized onto `work.meta["authors"]` and `WorkContribution(role="author")`, the `"translator"` `WorkContribution` remains intact, and child `Manifestation.meta` is not polluted with Work-level `"authors"`.

#### Scenario: Unrepairable empty-author Work is idempotent across dry-runs
- **GIVEN** a `Work` with `work.meta["authors"] = ["Unknown"]` and no recoverable author in attached manifestations
- **WHEN** `repair_work_authors(dry_run=False)` runs followed by `repair_work_authors(dry_run=True)`
- **THEN** the second run reports `0` works needing repair.

#### Scenario: Manifestation display resolves relational Work contributor when JSON meta is empty
- **GIVEN** a `Manifestation` whose parent `Work` has `work.meta["authors"] = []` but has a relational `WorkContribution` linked to `Contributor(name="Stanisław Lem")`
- **WHEN** `_resolve_manifestation_display_author` resolves the display author
- **THEN** it returns `"Stanisław Lem"` and does not fail on duck-typed manifestation stubs lacking `.author`.

### Requirement: Hidden-Aware FTS & Multi-Status Wishlist Safety in Shared Collections

`fetch_shared_collection_by_token` (`app/api/public_items.py`) and `SearchService.search_items` (`app/core/search_service.py`) SHALL exclude hidden items (`is_hidden = TRUE`) inside the SQL query *before* applying `LIMIT` on public/shared views, SHALL accept both `str` and `list[str]` for `filters["status"]` and `filters["tags"]` without raising `TypeError`, SHALL use dialect-safe SQLAlchemy 2.0 queries for wishlist intents without full-JSON `Work.meta` substring scans, and SHALL escape `%`, `_`, and `\` wildcards via `escape_ilike_term()`.

#### Scenario: Shared collection search returns public items despite 50+ hidden FTS matches
- **GIVEN** a user owns 55 hidden items (`is_hidden=True`) and 6 public items (`is_hidden=False`) matching `"Dom"` with `content_type="text"` on PostgreSQL
- **WHEN** `GET /api/public/share/<token>` is requested for that filtered view
- **THEN** `_pg_item_fts` filters `i.is_hidden = FALSE` prior to `LIMIT` and returns all 6 public items.

#### Scenario: Multi-status shared view with wishlist and reading statuses does not raise TypeError
- **GIVEN** a `SharedCollection` with `filters = {"status": ["want_to_read", "reading"], "query": "Dune"}`
- **WHEN** `fetch_shared_collection_by_token` executes on either PostgreSQL or SQLite
- **THEN** it returns matching public items and `UserWorkIntent` wishlist entries with HTTP 200 and zero `TypeError` or `OperationalError`.

### Requirement: Bounded ISBN Timeout, BN Outbound Telemetry & OpenAPI Contract Accuracy

`app/utils/isbn.py` SHALL never allocate a connect timeout exceeding the remaining `max_duration` budget, SHALL record outbound telemetry (`record_outbound_telemetry`) for Biblioteka Narodowa lookups, and `app/api/docs.py` SHALL accurately document HTTP `302` responses and request payloads for `/api/auth/login/apple`, `/api/auth/callback/apple`, `/api/auth/exchange`, and `/api/admin/maintenance/repair-authors`.

#### Scenario: Remaining ISBN lookup budget below 1.5s is respected
- **GIVEN** `deadline - time.monotonic()` equals `0.2` seconds during an ISBN fallback chain
- **WHEN** `_calc_timeout(deadline)` computes `(connect_timeout, read_timeout)`
- **THEN** `connect_timeout <= 0.2` and `read_timeout <= 0.2`.

#### Scenario: Admin author repair runs safely via background task with audit log
- **GIVEN** an authenticated administrator calls `POST /api/admin/maintenance/repair-authors` with `{"dry_run": false}`
- **WHEN** the endpoint processes the request
- **THEN** it dispatches via `submit_task` without blocking the Gunicorn worker indefinitely and records an `EntityAuditLog` entry.
