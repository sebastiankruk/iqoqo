# frbr/physical-attributes Specification

## Purpose

Provides explicit typed relational column storage, database indexing, and migration guarantees for FRBR Group 1 F3 Manifestation physical attributes (ISBN-13, publisher, and format type).

## Requirements

### Requirement: Dedicated Typed Storage for Manifestation Physical Attributes

The system SHALL store FRBR F3 Manifestation physical attributes (`isbn13`, `publisher`, and `format_type`) in dedicated, typed relational columns with database indexes on the `manifestations` table rather than inside unstructured JSON `meta` documents.

#### Scenario: Querying manifestations by ISBN-13

- **WHEN** a client or service looks up a manifestation by its 13-digit ISBN
- **THEN** the system SHALL resolve the record using the indexed `isbn13` column directly

#### Scenario: Filtering manifestations by publisher

- **WHEN** a client or catalog query filters manifestations by publisher
- **THEN** the system SHALL match against the dedicated `publisher` column

#### Scenario: Filtering manifestations by format type

- **WHEN** a client queries manifestations filtered by format type (e.g., hardcover, paperback, vinyl, dvd)
- **THEN** the system SHALL resolve the manifestation using the dedicated `format_type` column

### Requirement: Data Backfill and JSON Deprecation for Promoted Attributes

The migration pipeline SHALL backfill existing `isbn13`, `publisher`, and `format_type` data from the unstructured JSON `meta` column into the new typed columns, and SHALL purge the promoted keys from `meta` to eliminate duplicate state.

#### Scenario: Legacy meta attributes backfilled to typed columns

- **WHEN** the promotion migration runs against existing manifestations containing `isbn13`, `publisher`, or `format_type` in `meta`
- **THEN** the system SHALL copy those values into the corresponding typed relational columns without data loss

#### Scenario: Clean meta JSON document post-migration

- **WHEN** a manifestation record is retrieved after the promotion migration has completed
- **THEN** its `meta` JSON column SHALL NOT contain the promoted `isbn13`, `publisher`, or `format_type` keys

### Requirement: Service Layer Column-First Physical Attributes Access

The FRBR service layer SHALL read physical attributes (`isbn13`, `publisher`, `format_type`) directly from typed relational columns and SHALL persist them into typed columns upon creation and update.

#### Scenario: Manifestation creation persists typed columns

- **WHEN** a new manifestation is created with `isbn13`, `publisher`, or `format_type` supplied
- **THEN** the system SHALL store those values into the typed relational columns and omit them from the `meta` JSON document

#### Scenario: Manifestation update modifies typed columns

- **WHEN** an update request modifies `isbn13`, `publisher`, or `format_type` for an existing manifestation
- **THEN** the system SHALL persist the new values directly into the typed columns

### Requirement: Backward-Compatible API Serialization and Frontend Contracts

The system API responses and frontend type contracts SHALL expose `isbn13`, `publisher`, and `format_type` as first-class attributes while maintaining backward compatibility for existing consumers.

#### Scenario: Serializing manifestation detail response

- **WHEN** a client requests manifestation details via the catalog API
- **THEN** the response payload SHALL include `isbn13`, `publisher`, and `format_type` at the entity root level alongside the pruned `meta` object

#### Scenario: Frontend type contracts reflect physical attributes

- **WHEN** client applications import `Manifestation` or `CatalogEntry` interfaces from `frontend/types/frbr.ts`
- **THEN** the TypeScript definitions SHALL declare `isbn13`, `publisher`, and `format_type` as typed fields
