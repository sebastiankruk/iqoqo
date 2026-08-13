# item-ingestion Specification

## Purpose

Handle item ingestion into the collection, including scanner barcode lookup and metadata resolution from local database records and external provider strategies.

## Requirements

### Requirement: Discard Corrupted Local Manifestation in Scanner Preview

The system SHALL evaluate local database manifestations during scanner barcode lookup (`GET /api/lookup/<query>`) and discard cache hits if normalized metadata resolves to title `"Unknown Title"` with no author information, falling through to external metadata provider lookup strategies.

#### Scenario: Lookup barcode with corrupted local database manifestation

- **WHEN** user requests barcode lookup for an ISBN existing in local database with corrupted or missing title and author
- **THEN** system SHALL bypass returning local cache record directly, execute external provider lookup strategy, and return rich metadata linked to existing manifestation ID
