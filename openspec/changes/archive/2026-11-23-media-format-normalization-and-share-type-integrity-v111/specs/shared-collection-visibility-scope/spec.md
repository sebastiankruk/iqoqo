## ADDED Requirements

### Requirement: Share Collection Filter Schema Normalization and Persistence

`POST /api/sharing/` (`SharedCollectionCreateSchema`) SHALL accept, validate, and canonicalize media-category filters (`tags` and `category` aliases normalized via `FORMAT_ALIAS_TO_CATEGORY`) and carrier-format filters (`format` / `formats` validated/normalized against `MediaFormat` constants and `FormatNormalizer`) inside `SharedCollection.filters`, rejecting invalid non-empty filter types or unrecognized format values with HTTP `400` and preserving fail-closed empty arrays when explicitly supplied.

#### Scenario: Creating a music and vinyl filtered share persists normalized category and format filters

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `{"name": "My Vinyl", "filters": {"tags": ["audio"], "format": ["vinyl"]}}`
- **WHEN** `SharedCollectionCreateSchema` validates the request
- **THEN** the persisted `SharedCollection.filters` MUST store canonicalized `tags: ["music"]` and `format: ["vinyl"]` alongside `visibility_scope`.

#### Scenario: Creating a share link with an invalid carrier format filter is rejected

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `{"name": "Bad Share", "filters": {"format": ["nonexistent_carrier"]}}`
- **WHEN** `SharedCollectionCreateSchema` validates the request
- **THEN** the backend MUST reject the request with HTTP `400`.

### Requirement: Share Creation UI Filter Capture for Category and Format

`ShareCollectionDialog` SHALL capture active `"format"` filters alongside `"category"` and `"status"` filters from the collection view, transmit them as `filters.format` in `POST /api/sharing/`, and include active format filters in the localized default share name (`en.json` and `pl.json` using sentence case for Polish).

#### Scenario: Collector creates a share link from a category and format filtered collection

- **GIVEN** an authenticated collector viewing `/collection` with active filters `[{ type: "category", value: "music" }, { type: "format", value: "vinyl" }]`
- **WHEN** the collector opens `ShareCollectionDialog` and submits the share form
- **THEN** the dialog MUST pre-populate a default share name reflecting the active filters and MUST transmit `filters: { visibility_scope: "public_only", tags: ["music"], format: ["vinyl"] }` in `POST /api/sharing/`.
