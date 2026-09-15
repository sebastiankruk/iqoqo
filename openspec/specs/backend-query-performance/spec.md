# backend-query-performance Specification

## Purpose

Defines requirements for database-level pagination, eager relationship loading, taxonomy query caching, and efficient roadmap reordering to prevent memory exhaustion and database load spikes.

## Requirements

### Requirement: Database-Level Query Pagination and Deduplication
The system SHALL execute pagination slicing and deduplication directly within database queries using SQL `LIMIT`, `OFFSET`, and `DISTINCT ON` rather than post-filtering in Python process memory.

#### Scenario: Requesting paginated inventory items

- **WHEN** an API client requests a page of items from a large collection
- **THEN** the database query includes explicit `LIMIT` and `OFFSET` clauses, returning only the requested slice of rows

#### Scenario: Requesting distinct global fresh arrivals

- **WHEN** the dashboard fetches latest arrivals across library items
- **THEN** unique entity deduplication is performed at the database level via `DISTINCT ON`

### Requirement: Eager Loading for Virtual Items and Hierarchies
The system SHALL eagerly load related entities in batch using SQLAlchemy loading strategies (`selectinload` or `joinedload`) to prevent N+1 query storms during list retrieval.

#### Scenario: Retrieving virtual items list

- **WHEN** an API endpoint queries virtual items across multiple collections
- **THEN** related manifestation and work models are fetched in batched queries rather than executing individual queries per item

### Requirement: Taxonomy Caching and Differential Roadmap Ordering
The system SHALL cache taxonomy facet trees in Redis with scheduled background invalidation, and update reading roadmap sequences using differential indexing.

#### Scenario: Querying library taxonomy tree

- **WHEN** the frontend queries available library taxonomy facets
- **THEN** precomputed taxonomy hierarchies are returned directly from Redis cache

#### Scenario: Repositioning item in reading roadmap

- **WHEN** a user drags an item to a new position in the roadmap
- **THEN** the position index is updated differentially without rewriting sequential ranks for all other items in the collection

### Requirement: Modular QR Code Utility Extraction
The system SHALL isolate QR code SVG generation into a dedicated utility module with strict input validation.

#### Scenario: Rendering item badge QR code

- **WHEN** an item QR code is requested
- **THEN** the SVG payload is produced by the centralized utility with guaranteed bounded execution
