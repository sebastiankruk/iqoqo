## ADDED Requirements

### Requirement: Search Filtering by Multi-field Bibliographic Attributes
The shared collection view SHALL filter displayed items by search queries matching titles with diacritic insensitivity, contributor names, manifestation barcodes, UPC identifiers, and catalog numbers.

#### Scenario: Shared collection search matches diacritics and secondary identifiers
- **WHEN** an unauthenticated visitor searches for a query containing Polish or international diacritics (e.g. "insulinooporności") or an item barcode
- **THEN** the shared collection endpoint and client UI SHALL filter and return matching items without dropping diacritic variants.

### Requirement: Dynamic Public URL Resolution on Native Mobile Environments
The mobile client and shared UI components SHALL resolve absolute share URLs and public RSS feed endpoints against the active server instance rather than defaulting to local device origins.

#### Scenario: Sharing a link or accessing feed on mobile device
- **WHEN** a user taps "Share View", copies a share link, or opens the public RSS feed in a native iOS or Android shell
- **THEN** the URL SHALL resolve against the current server instance origin (`getSyncInstanceUrl()`)
- **AND** feed URLs SHALL open via the external system browser (`@capacitor/browser`) rather than failing within the native WebView.
