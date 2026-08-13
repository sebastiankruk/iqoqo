## Purpose

Define safeguards for data validation, cache consistency, and reliable migration backfills.

## Requirements

### Requirement: Barcode validation without silent truncation
The system SHALL NOT silently truncate barcode strings in `_record_scan_telemetry`. Instead, barcodes exceeding 128 characters SHALL be rejected at the Pydantic schema validation layer (`ScanBarcodeSchema`) with a descriptive error.

#### Scenario: Barcode exceeds 128 characters

- **WHEN** a barcode longer than 128 characters is submitted to the scanner API
- **THEN** the system SHALL return HTTP 422 with a validation error, not silently truncate

### Requirement: Cache key normalization
The system SHALL normalize and sort query parameters alphabetically inside `make_facets_cache_key()` before generating Redis cache key strings, ensuring that `?a=1&b=2` and `?b=2&a=1` produce identical cache keys.

#### Scenario: Reordered query params hit same cache

- **WHEN** two requests to `/api/stats/facets` arrive with identical parameters in different order
- **THEN** they SHALL resolve to the same Redis cache key and return cached data

### Requirement: Migration backfill deterministic pagination
The Alembic migration `e3f891ab45c2` SHALL use deterministic keyset pagination that only advances `last_id` past rows that were actually updated, preventing silent skipping of unprocessed records.

#### Scenario: Row with whitespace-only title

- **WHEN** a row has `title = "   "` (whitespace) and `sort_title IS NULL`
- **THEN** the backfill loop SHALL not skip past that row without processing it

### Requirement: Migration startup performance
The Alembic migration `e3f891ab45c2` SHALL NOT include artificial `time.sleep()` delays that block container startup.

#### Scenario: Container startup with large dataset

- **WHEN** `flask db upgrade` runs on a database with 50k+ items
- **THEN** the migration SHALL complete without artificial sleep delays that risk Docker health check timeouts

### Requirement: Migration backfill releases locks after each batch
The PostgreSQL execution path of migration `e3f891ab45c2` SHALL commit each completed backfill batch before processing the next batch, releasing transaction locks without waiting for the entire migration to finish.

#### Scenario: Large backfill processes independent committed batches

- **WHEN** migration `e3f891ab45c2` processes multiple batches on PostgreSQL
- **THEN** the migration SHALL issue a commit after each completed batch
- **AND** a later batch failure SHALL leave previously committed batches durable and allow the migration to resume safely
