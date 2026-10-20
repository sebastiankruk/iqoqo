## ADDED Requirements

### Requirement: Scanner Exemplar Barcode Resolution
The barcode scanner workflow SHALL query and resolve physical `Item.local_barcode` tags in addition to standard publication ISBN/UPC barcodes.

#### Scenario: Scanning existing local barcode retrieves inventory item
- **WHEN** a user scans an asset sticker matching an existing `Item.local_barcode`
- **THEN** the system resolves the scan to the existing library Item and its parent Manifestation.
