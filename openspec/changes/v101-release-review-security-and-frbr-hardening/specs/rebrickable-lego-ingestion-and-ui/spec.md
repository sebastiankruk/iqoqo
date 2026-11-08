# Delta Specification: Rebrickable LEGO Ingestion and UI Projection (`C108c`)

## ADDED Requirements

### Requirement: Rebrickable Set Number Validation, N+1 Elimination, and First-Class LEGO FRBR Columns (`C-02`, `C-03`)

`app/utils/rebrickable.py`, `app/core/ingest.py`, and `app/api/scanner.py` MUST prevent URL path traversal on set numbers, avoid per-candidate N+1 `/minifigs/` HTTP requests during search, populate first-class `Manifestation` columns (`ean`, `upc`, `format_type`), and prioritize `570201` LEGO GS1 barcodes.

#### Scenario: Reject path-traversal or free-text strings in `fetch_rebrickable_set`

- **GIVEN** a non-set-number query such as `"../../users/profile"` or `"Star Wars Millennium Falcon"`
- **WHEN** `fetch_rebrickable_set()` or `_fetch_minifig_count()` is called
- **THEN** it MUST validate the normalized string against `^\d{3,7}(?:-\d{1,2})?$` and return `None` / `0` without issuing an outbound HTTP request with an unvalidated path segment.

#### Scenario: Avoid N+1 `/minifigs/` requests during `search_rebrickable_sets`

- **GIVEN** a search query returning 10 candidate sets from `GET /api/v3/lego/sets/`
- **WHEN** `search_rebrickable_sets()` formats the candidate list
- **THEN** it MUST NOT execute per-candidate `/minifigs/` HTTP requests, keeping candidate search latency bounded.

#### Scenario: Populate `Manifestation.ean`, `Manifestation.upc`, `Manifestation.format_type`, and `Work.meta["theme"]` for LEGO sets

- **GIVEN** LEGO metadata ingested via either `IngestService.ingest_lego_from_barcode()` or `IngestService.ingest_from_meta()`
- **WHEN** the FRBR Work, Expression, and Manifestation are persisted
- **THEN** `Expression.content_type` MUST equal `"lego"`, `Manifestation.format_type` MUST be populated (e.g. `"standard_set"`), `Manifestation.ean` (13-digit) or `Manifestation.upc` (12-digit) MUST be set, and `Work.meta["theme"]` MUST be preserved.

#### Scenario: Route `570201xxxxxxx` LEGO GS1 barcode to LEGO even when scanner tab defaults to `book`

- **GIVEN** a 13-digit barcode starting with `"570201"` (e.g. `"5702018068229"`)
- **WHEN** `GET /api/scanner/lookup/5702018068229?format=book` is called
- **THEN** the scanner endpoint MUST recognize the official LEGO GS1 prefix, query `LegoLookupStrategy`, and return/store `category: "lego"` and `format: "standard_set"`.
