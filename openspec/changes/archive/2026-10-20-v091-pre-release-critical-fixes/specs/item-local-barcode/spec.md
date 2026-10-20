## ADDED Requirements

### Requirement: Scanner Local Barcode Resolution and Manual Search Ingestion
The barcode scanner and manual text search workflow (`GET /api/lookup/<code>` and `POST /api/scan`) SHALL scope `Item.local_barcode` lookups strictly to the authenticated user (`Item.owner_id == g.user_id`) and SHALL allow ingesting items from `payload.meta` when a manual text-search selection lacks a numeric barcode or pre-existing `manifestation_id`.

#### Scenario: Manual text search candidate without numeric barcode is added to library
- **WHEN** a user searches by text in `/scan`, selects a candidate from the disambiguation list, and submits `POST /api/scan` with `meta` populated and `barcode` empty
- **THEN** `_validate_scan_request` accepts the request and `scan_barcode` ingests or resolves the `Manifestation` from `payload.meta` without returning `"Barcode or Manifestation ID is required"`

#### Scenario: Cross-user local_barcode tag does not leak across collectors
- **WHEN** User A assigns `local_barcode = "SHELF-A1"` to a private or public Item and User B scans or looks up `"SHELF-A1"`
- **THEN** `_find_locally` and `lookup_barcode_preview` do not match User A's Item, do not expose User A's `item_id`, and do not set `already_in_collection = True` for User B
