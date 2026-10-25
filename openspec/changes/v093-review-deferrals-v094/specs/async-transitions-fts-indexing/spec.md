## MODIFIED Requirements

### Requirement: Background FTS Vector Recomputation

The system SHALL queue and batch-update full-text search vectors asynchronously without blocking transition writes, using a shared dialect-aware helper (`build_fts_tsvector_expr`) that wraps text columns in `func.unaccent(...)` on PostgreSQL and omits `unaccent` on SQLite. Downward Alembic migrations (`v0_8_4_fts_unaccent`) SHALL NOT drop the PostgreSQL `unaccent` extension required by earlier migrations (`v0_8_2`).

#### Scenario: Transition writes return immediately

- **WHEN** An item status or custody changes
- **THEN** The HTTP response returns 200 immediately, enqueuing Celery FTS re-indexing in background.

#### Scenario: Shared dialect-aware FTS expression builder

- **WHEN** `SearchService.reindex_manifestations_batch`, `reindex_items_batch`, or `update_search_vector` constructs a `tsvector` update expression
- **THEN** It uses `build_fts_tsvector_expr` to apply `unaccent` only when the active database dialect is `postgresql`.

#### Scenario: Downgrading v0_8_4 preserves unaccent extension

- **WHEN** `alembic downgrade` executes `v0_8_4_fts_unaccent.downgrade()`
- **THEN** The `unaccent` PostgreSQL extension remains installed so `v0_8_2` indexes continue to function.
