# rebrickable-lego-ingestion-and-ui Specification

## Purpose

Enable automated ingestion of LEGO sets via Rebrickable (by barcode or LEGO Set Number) and project LEGO-specific attributes across the UI.

## Requirements

### Requirement: Rebrickable LEGO Lookup Strategy & Graceful Fallback

The scanner API (`/api/scanner/lookup`) SHALL support `lego` media lookups by EAN/UPC barcode and by LEGO Set Number (`10318` or `10318-1`) via `app/utils/rebrickable.py` (routed through SSRF-safe `http_client.py`), and SHALL fall back gracefully to manual entry with pre-filled identifiers if Rebrickable is unconfigured or returns no match.

#### Scenario: Collector looks up LEGO set `10318`

- **GIVEN** `REBRICKABLE_API_KEY` is configured (Fernet-encrypted at rest)
- **WHEN** the user queries `10318` with `media_type="lego"`
- **THEN** `LegoLookupStrategy` normalizes `10318` to `10318-1`, fetches the set metadata (`title`, `piece_count`, `minifig_count`, `year`, `cover_url`), and records `prov:wasDerivedFrom` `"rebrickable"`.

#### Scenario: Rebrickable lookup fails or API key is unconfigured

- **GIVEN** `REBRICKABLE_API_KEY` is unset or external lookup fails
- **WHEN** the user scans a LEGO barcode
- **THEN** the API returns a graceful not-found response without generating fake metadata, pre-filling the scanned barcode in the manual entry form.

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
