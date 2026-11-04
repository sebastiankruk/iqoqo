# shared-collection-ui Specification

## Purpose

TBD - created by archiving change clean-shared-collection-ui. Update Purpose after archive.

## Requirements

### Requirement: Global Navigation in Shared View

The system SHALL ensure that public shared collection pages provide global site navigation elements (Navbar, Footer) to maintain context and continuity for unauthenticated users.

#### Scenario: Unauthenticated user views shared collection

- **WHEN** an unauthenticated user navigates to a `/share/[token]` link
- **THEN** the page renders the shared collection along with the global site Navbar and Footer components, without triggering redirection or 401 errors.

### Requirement: Search Filtering by Multi-field Bibliographic Attributes with FTS Parity
The shared collection view SHALL filter displayed items by search queries matching titles with diacritic insensitivity, contributor names, manifestation barcodes, UPC identifiers, and catalog numbers. When running on PostgreSQL, the endpoint SHALL query through `SearchService.search_items` to ensure exact parity with full-text search results on `/collection`.

#### Scenario: Shared collection search matches diacritics and secondary identifiers
- **WHEN** an unauthenticated visitor searches for a query containing Polish or international diacritics (e.g. "insulinooporności") or an item barcode
- **THEN** the shared collection endpoint and client UI SHALL filter and return matching items without dropping diacritic variants.

#### Scenario: Shared collection search avoids false positives from description and address dumps
- **WHEN** a user searches for a short query token such as "dom" and creates a shared collection link
- **THEN** the shared collection endpoint SHALL NOT match items solely because "dom" is a substring within manufacturer addresses (e.g. "ul. Domaniewska") or book descriptions (e.g. "powrotu do domu")
- **AND** the result count SHALL match the items displayed on `/collection`.

### Requirement: Strict Anti-Localhost Public URL Resolution on Native Mobile Environments
The mobile client and shared UI components SHALL resolve absolute share URLs and public RSS feed endpoints against the active server instance. In native mobile shells or local host environments, the resolved public base origin SHALL never return `localhost` or `capacitor://localhost`, falling back to the canonical public domain (`NEXT_PUBLIC_FRONTEND_URL` / `https://preview.iqoqo.cc`).

#### Scenario: Sharing a link or accessing feed on mobile device
- **WHEN** a user taps "Share View", copies a share link, or opens the public RSS feed in a native iOS or Android shell
- **THEN** the URL SHALL resolve against the current server instance origin (`getSyncInstanceUrl()`)
- **AND** if the instance URL is not configured or contains localhost, it SHALL fall back to `https://preview.iqoqo.cc`
- **AND** feed URLs SHALL open via the external system browser (`@capacitor/browser`) rather than failing within the native WebView.

### Requirement: Author Attribution Across FRBR Work and Manifestation Tiers in Shared Views
The shared collection API SHALL inspect both `Work.meta["authors"]` and `Manifestation.meta["authors"]` to populate authors in shared collection item payloads.

#### Scenario: Shared item author population
- **WHEN** an item's manifestation metadata does not contain an inline `authors` key, but its linked FRBR Work metadata specifies authors
- **THEN** the shared collection endpoint SHALL return the Work's author array in the item's `authors` attribute rather than returning an empty list.
