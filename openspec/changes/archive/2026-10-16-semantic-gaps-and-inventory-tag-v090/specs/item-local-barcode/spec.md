## Purpose

Provides physical exemplar-level identification via local barcodes and inventory tags on Items (F5), distinctly separated from Manifestation-level ISBNs or UPCs, to support physical library stickers, shelf management, and federated circulation.

## ADDED Requirements

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
