## MODIFIED Requirements

### Requirement: Localized scanner top bar and clear policy naming

The scanner top bar SHALL present a single-line compact control row containing localized **Format**, **Destination Policy** ("Shelf", "Wishlist", "Catalog Only"), and optional **Batch Mode** controls, followed by a full-width (100%) unified lookup bar when active. All top bar headers, selector pills, menu options, and tooltips SHALL be fully translated in both English and Polish without horizontal clipping on mobile viewports (`>= 360px`).

#### Scenario: User opens scanner and views top bar

- **WHEN** the user opens `/scan` on a mobile or desktop viewport
- **THEN** the top bar displays localized titles, the compact single-line control row with Format (`format-selector-trigger`), Destination Policy (`policy-selector-trigger`: "Shelf", "Wishlist", "Catalog Only"), and Batch Mode (`batch-scan-toggle`) with zero horizontal icon clipping
- **AND** the unified search input (`unified-lookup-input`) spans 100% of the available container width below the control row

#### Scenario: User changes policy mode

- **WHEN** the user opens the Destination Policy selector (`policy-selector-trigger`) and selects "Catalog Only", "Wishlist", or "Shelf"
- **THEN** the active policy pill updates immediately, displays localized guidance, and persists across scans without ambiguous terminology

#### Scenario: User switches media format via compact selector menu

- **WHEN** the user activates the Format selector pill (`format-selector-trigger`)
- **THEN** a localized menu opens displaying every registered format in `SCAN_FORMATS` with icon and full label
- **AND** selecting a format updates the active pill label immediately and closes the menu

## ADDED Requirements

### Requirement: Streamlined two-tab scanner bottom sheet without duplicate search

The scanner bottom sheet SHALL present two capture mode tabs (`Barcode` and `Snap Cover`), removing the duplicate `Manual Search` tab while retaining a direct secondary `Enter details manually` fallback trigger (`enter-manually-link`) and automatic manual-entry fallback on lookup failure/timeout.

#### Scenario: User views the bottom sheet capture tabs and triggers manual entry

- **WHEN** the user views the scanner bottom sheet
- **THEN** only `Barcode` (`scanner-tab-barcode`) and `Snap Cover` (`scanner-tab-cover`) tabs are displayed (`scanner-tab-manual` is absent)
- **AND** activating `enter-manually-link` opens `ManualEntryForm` directly without requiring an intermediate search input inside the sheet
