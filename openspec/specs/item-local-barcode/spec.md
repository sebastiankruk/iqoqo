# item-local-barcode Specification

## Purpose

Provides physical exemplar-level identification via local barcodes and inventory tags on Items (F5), distinctly separated from Manifestation-level ISBNs or UPCs, to support physical library stickers, shelf management, and federated circulation.

## Requirements

### Requirement: Local Barcode Exemplar Tracking

The system SHALL support an optional, indexed `local_barcode` string identifier on each Item (F5) entity representing a physical shelf label, barcode sticker, or local inventory asset tag.

#### Scenario: Setting local barcode during item creation

- **WHEN** an item is created via `POST /api/items` with a non-empty `local_barcode` payload
- **THEN** the system stores the `local_barcode` on the Item record and returns it in the item detail response.

#### Scenario: Updating item local barcode

- **WHEN** an authenticated custodian or owner updates an item via `PUT /api/items/<id>` with a new `local_barcode` value
- **THEN** the system persists the updated value and reflects the change in subsequent item retrievals.

#### Scenario: Clearing item local barcode

- **WHEN** an item update request provides `local_barcode: null` or an empty string
- **THEN** the system clears the local barcode on the Item without affecting manifestation identifiers.

### Requirement: Ontological Distinction from Manifestation Identifiers

The system SHALL preserve strict ontological boundaries between Manifestation-level publication identifiers (`isbn`, `ean`, `upc`) and Item-level exemplar identifiers (`local_barcode`).

#### Scenario: Coexistence of manifestation ISBN and item local barcode

- **WHEN** an Item has a `local_barcode` and its parent Manifestation has an ISBN-13
- **THEN** both identifiers are exposed in their respective FRBR tiers without collisions, overwrites, or cross-tier pollution.

### Requirement: RDF Graph Barcode Serialization

The system SHALL serialize `iqoqo:local_barcode` onto the Item RDF node when exporting or streaming Linked Open Data collection graphs.

#### Scenario: Item with local barcode emits RDF triple

- **WHEN** A collection RDF export is generated containing an Item with a `local_barcode`
- **THEN** The RDF graph contains the triple `<item_uri> iqoqo:local_barcode "VALUE"`.

### Requirement: Physical Item Condition Tracking

The system SHALL accept and persist the physical `condition` of an Item across update endpoints and return it in item detail responses.

#### Scenario: Condition updated and retrieved

- **WHEN** An authenticated owner submits `PUT /api/items/<id>` with `condition: "near_mint"`
- **THEN** The value is persisted and returned in the item detail response `data.condition`.

### Requirement: Collection Link Ownership Validation

The system SHALL verify that any `collection_id` specified during item creation is owned by the authenticated caller.

#### Scenario: Item creation rejected for unowned collection

- **WHEN** An item is created with `collection_id` belonging to a different user or non-existent
- **THEN** The endpoint returns 404 Not Found without creating the link.

### Requirement: Scanner Exemplar Barcode Resolution
The barcode scanner workflow SHALL query and resolve physical `Item.local_barcode` tags in addition to standard publication ISBN/UPC barcodes.

#### Scenario: Scanning existing local barcode retrieves inventory item

- **WHEN** a user scans an asset sticker matching an existing `Item.local_barcode`
- **THEN** the system resolves the scan to the existing library Item and its parent Manifestation.

### Requirement: Scanner Local Barcode Resolution and Manual Search Ingestion
The barcode scanner and manual text search workflow (`GET /api/lookup/<code>` and `POST /api/scan`) SHALL scope `Item.local_barcode` lookups strictly to the authenticated user (`Item.owner_id == g.user_id`) and SHALL allow ingesting items from `payload.meta` when a manual text-search selection lacks a numeric barcode or pre-existing `manifestation_id`.

#### Scenario: Manual text search candidate without numeric barcode is added to library

- **WHEN** a user searches by text in `/scan`, selects a candidate from the disambiguation list, and submits `POST /api/scan` with `meta` populated and `barcode` empty
- **THEN** `_validate_scan_request` accepts the request and `scan_barcode` ingests or resolves the `Manifestation` from `payload.meta` without returning `"Barcode or Manifestation ID is required"`

#### Scenario: Cross-user local_barcode tag does not leak across collectors

- **WHEN** User A assigns `local_barcode = "SHELF-A1"` to a private or public Item and User B scans or looks up `"SHELF-A1"`
- **THEN** `_find_locally` and `lookup_barcode_preview` do not match User A's Item, do not expose User A's `item_id`, and do not set `already_in_collection = True` for User B
