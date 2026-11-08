# lego-allegro-retail-catalog-lookup Specification

## Purpose
Enable retail LEGO barcode and candidate lookups through Allegro API as a primary fallback when Rebrickable key is unconfigured or does not match a European retail EAN barcode.

## Requirements

### Requirement: Allegro Retail LEGO Barcode Lookup Fallback
The `LegoLookupStrategy` SHALL attempt metadata resolution via `fetch_allegro_metadata(cleaned_barcode)` when Rebrickable barcode lookup returns no match or is unconfigured, returning a normalized LEGO manifestation with `provider="allegro"`.

#### Scenario: Collector scans retail LEGO barcode without Rebrickable match

- **GIVEN** an EAN-13 barcode `5702018068229`
- **WHEN** Rebrickable returns no metadata
- **AND** Allegro API returns product metadata for `5702018068229`
- **THEN** `LegoLookupStrategy.lookup()` returns a dictionary containing `title`, `barcode`, `cover_url`, `set_number`, and `provider="allegro"`.

### Requirement: LEGO Candidate Search with Allegro Enrichment
`LegoLookupStrategy.lookup_candidates()` and `/api/scanner/lookup` SHALL query Allegro product candidates when searching for LEGO sets by free-text title or theme.

#### Scenario: Collector searches LEGO set candidates

- **GIVEN** a query string `"LEGO Concorde"` with `category="lego"`
- **WHEN** candidate search is performed
- **THEN** candidates from Rebrickable and Allegro are aggregated up to `max_results`.
