# zero-downtime-migrations Specification

## Purpose
TBD - created by archiving change container-script-hardening. Update Purpose after archive.
## Requirements
### Requirement: Zero-Downtime Migration Backfills
Data backfill operations within Alembic migrations (specifically `e3f891ab45c2`) MUST process rows in chunks using explicit `LIMIT`/`OFFSET` or Primary Key ranges, and include short sleep intervals between chunks to yield database locks.

#### Scenario: Running a large backfill migration

- **WHEN** Alembic executes a backfill migration on a table with millions of rows
- **THEN** the migration processes the data in batches of a defined size (e.g., 1000 rows)
- **THEN** it yields the database lock momentarily between batches
- **THEN** the application remains responsive during the migration process
