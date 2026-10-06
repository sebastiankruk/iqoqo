## ADDED Requirements

### Requirement: Migration backfill releases locks after each batch
The PostgreSQL execution path of migration `e3f891ab45c2` SHALL commit each completed backfill batch before processing the next batch, releasing transaction locks without waiting for the entire migration to finish.

#### Scenario: Large backfill processes independent committed batches

- **WHEN** migration `e3f891ab45c2` processes multiple batches on PostgreSQL
- **THEN** the migration SHALL issue a commit after each completed batch
- **AND** a later batch failure SHALL leave previously committed batches durable and allow the migration to resume safely
