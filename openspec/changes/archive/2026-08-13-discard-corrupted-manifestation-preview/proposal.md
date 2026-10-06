# Proposal: Discard Corrupted Manifestation Records in Scanner Preview

## Why

During barcode scanner lookups, manifestations that were previously ingested into the local database with missing or corrupted metadata (e.g. "Unknown Title" and no author) were returned directly from the local DB. This prevented the scanner preview from querying external metadata providers (Google Books, Open Library), causing valid books to display as "Unknown Title" in the UI.

## What Changes

- Modified `lookup_barcode_preview` in `app/api/scanner.py` to evaluate local database manifestations.
- If a cached local manifestation's metadata resolves to "Unknown Title" and lacks author information, it is treated as a cache miss.
- Fallthrough to external metadata providers resolves rich metadata, links to the existing manifestation ID, and updates the local record.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `item-ingestion`: Re-evaluate local DB manifestation metadata validity during scanner lookup and force external fallback when local records are corrupted or incomplete.

## Impact

- `app/api/scanner.py`: Scanner barcode preview lookup endpoint.
- `tests/test_api_scanner.py`: Added regression unit test `test_lookup_barcode_discards_legacy_broken_db_record`.
