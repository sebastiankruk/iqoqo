## Why

Dev-note finding (#ux #custodian #v083, scheduled to v0.8.4): "if one provider does not deliver cover pages - but we got metadata from it - we are stuck with empty cover instead of merging metadata+covers across different providers... separate from having a smart way of just filling in the blanks on main fields like cover or even author by merging different sources". Release planning: v0.8.x, C57 (target v0.8.4).

Premises verified against code:
- **Confirmed: First-hit wins stops lookup prematurely.** In `app/utils/isbn.py:470-474`, `fetch_isbn_metadata()` returns immediately when Google Books returns `SUCCESS`. If Google Books provides metadata but no cover art (`cover_url is None`), Open Library is never queried.
- **Confirmed: Identifiers are shared and authoritative.** Both providers resolve the exact same canonical ISBN-13. Querying secondary providers for missing fields on the exact same identifier poses zero risk of edition cross-contamination.
- **Confirmed: Provenance tracking.** `app/core/frbr_service.py:2009-2040` already formats `prov:wasDerivedFrom` triples in RDF. Recording per-field provenance allows Linked Data graphs to attribute text metadata and cover art to their distinct original sources.

## What Changes

- **Automated Metadata & Cover Gap-Filling:** In `app/utils/isbn.py` (and media ingest adapters), when a primary provider resolves metadata but lacks a valid cover image or essential attributes (e.g. `cover_url`, `authors`, `publisher`, `publication_date`), query secondary configured providers by the same identifier to fill empty fields.
- **Strict Precedence & Non-Overwriting:** Existing populated fields from the primary provider are never overwritten; only null/empty attributes are enriched.
- **Field-Level Provenance:** Record source attribution per field in `meta["provenance"]` (e.g. `{"title": "google_books", "cover_url": "open_library"}`), mapped into FRBR RDF `prov:wasDerivedFrom` serialization.
- **Bounded Latency Ceiling:** Set a global lookup timeout ceiling (3.0s total) so gap filling does not delay scanner responses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `book-provider-fallback-retry`: Extends lookup behavior to support multi-provider gap-filling when primary provider outcomes lack cover images or key bibliographic attributes.

## Impact

- **Backend:** `app/utils/isbn.py`, `app/core/ingest.py`, `app/utils/covers.py`, `app/core/frbr_service.py`.
- **Tests:** Pytest mocking partial provider payloads (Google Books with no cover + Open Library with cover) and asserting combined resolution with field-level provenance.
