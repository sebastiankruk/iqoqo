## MODIFIED Requirements

### Requirement: Migration batch commits release row locks incrementally
Alembic migration `e3f891ab45c2` SHALL execute explicit transaction commits after each batch update iteration during the ETL backfill loop, releasing row locks incrementally instead of holding them for the entire migration duration.

#### Scenario: Large table migration with batched commits

- **WHEN** migration `e3f891ab45c2` runs against a table with more than 1000 rows
- **THEN** the migration SHALL commit after each batch of rows (batch size configurable, default 500)
- **AND** row locks SHALL be released after each batch commit
- **AND** concurrent read queries SHALL not be blocked for the entire migration duration

#### Scenario: Migration is re-run on partially migrated database

- **WHEN** migration `e3f891ab45c2` is re-run after a partial completion (crash mid-batch)
- **THEN** the migration SHALL skip already-processed rows (idempotency check)
- **AND** the migration SHALL process remaining rows in batches

#### Scenario: Migration runs on empty database

- **WHEN** migration `e3f891ab45c2` runs against an empty database
- **THEN** the migration SHALL complete successfully without errors
- **AND** no batch processing SHALL occur (zero rows to process)
