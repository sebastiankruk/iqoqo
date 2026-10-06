## MODIFIED Requirements

### Requirement: Reversible batched ETL migration backfills normalized columns

The system SHALL provide a single Alembic migration revision that creates the new relational columns and indexes and backfills them from existing `meta` JSON data. The upgrade SHALL execute updates in distinct chunks (e.g. using `LIMIT` and `OFFSET`) to avoid monolithic table locking on large Postgres databases, preventing deployment timeouts. The migration SHALL be reversible (downgrade drops the new columns without touching `meta`) and SHALL leave `meta` intact as a fallback read source.

#### Scenario: Upgrade backfills existing rows

- **WHEN** the migration upgrade runs against a database containing rows with core properties only in `meta`
- **THEN** every such row SHALL have its core properties copied into the new relational columns in small batches with zero data loss, without acquiring a monolithic table lock

#### Scenario: Downgrade preserves meta data

- **WHEN** the migration downgrade runs after a successful upgrade
- **THEN** the new relational columns SHALL be dropped and all original `meta` JSON content SHALL remain unchanged
