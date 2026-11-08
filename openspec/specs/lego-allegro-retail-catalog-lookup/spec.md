# lego-allegro-retail-catalog-lookup Specification

## Purpose

Enable retail LEGO barcode and candidate lookups through the Allegro API as a primary fallback when Rebrickable is unconfigured or does not index a European retail EAN-13 barcode, and ensure scanner quick-lookup preserves the `lego` format hint so ingested LEGO sets are stored under the canonical `lego` / `standard_set` taxonomy rather than defaulting to `book`.

## Requirements

### Requirement: Allegro Retail LEGO Barcode Lookup Fallback

The `LegoLookupStrategy` SHALL attempt metadata resolution via `fetch_allegro_metadata(cleaned_barcode)` when Rebrickable barcode lookup returns no match or is unconfigured, extracting LEGO parameters (`Numer produktu`, `Numer zestawu`, `Kod producenta` -> `set_number`; `Liczba elementów`, `Liczba klocków` -> `piece_count`; `Seria`, `Linia` -> `theme`) and returning a normalized LEGO manifestation with `format="standard_set"`, `category="lego"`, and `provider="allegro"`.

#### Scenario: Collector scans retail LEGO barcode without Rebrickable match

- **GIVEN** an EAN-13 barcode `5702018068229`
- **WHEN** Rebrickable returns no metadata
- **AND** Allegro API returns product metadata for `5702018068229`
- **THEN** `LegoLookupStrategy.lookup()` returns a dictionary containing `title`, `barcode`, `cover_url`, `set_number`, `format="standard_set"`, `category="lego"`, and `provider="allegro"`.

### Requirement: LEGO Candidate Search with Allegro Enrichment

`LegoLookupStrategy.lookup_candidates()` and `/api/scanner/lookup` SHALL query Allegro product candidates when searching for LEGO sets by free-text title, set number, or theme.

#### Scenario: Collector searches LEGO set candidates

- **GIVEN** a query string `"LEGO Concorde"` with `category="lego"`
- **WHEN** candidate search is performed
- **THEN** candidates from Rebrickable and Allegro are aggregated up to `max_results`.

### Requirement: Scanner Quick-Lookup LEGO Format Preservation & Canonical Normalization

The scanner quick-lookup bar (`frontend/app/scan/page.tsx`) SHALL map the active `"lego"` media selection to `?format=lego`, and `app/api/scanner.py` (`_normalize_preview_meta`) SHALL map `format_hint="lego"` (and `"construction_set"`) to `MediaFormat.STANDARD_SET` (`"standard_set"`) so auto-saved manifestations bind to `Expression.content_type = "lego"` rather than defaulting to `"book"` / `"text"`.

#### Scenario: Collector scans LEGO barcode with LEGO icon selected in scanner quick-lookup

- **GIVEN** the collector has selected the `lego` media icon on `/scan`
- **WHEN** the collector submits barcode `5702018068229` in the quick-lookup input
- **THEN** the frontend requests `/api/lookup/5702018068229?format=lego`
- **AND** the backend normalizes and persists the resulting `Manifestation` with `format="standard_set"` and `Expression.content_type="lego"`.
