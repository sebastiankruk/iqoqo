# scanner-ux-streamline Specification

## Purpose

Streamlines the scanner user experience with clear policy naming ("Shelf" / "Wishlist" / "Catalog Only"), full TopBar localization, clean single-tap candidate selection, zero-refetch metadata passing, and preserved counter-rotating waiting animations.

## Requirements

### Requirement: Localized scanner top bar and clear policy naming

The scanner top bar SHALL present a single-line compact control row containing localized **Format**, **Destination Policy** ("Shelf", "Wishlist", "Catalog Only"), and optional **Batch Mode** controls, followed by a full-width (100%) unified lookup bar when active. All top bar headers, selector pills, menu options, and tooltips SHALL be fully translated in both English and Polish without horizontal clipping on mobile viewports (`>= 360px`). Passive selector pills on the control row—including **Format** (`format-selector-trigger`), **Destination Policy** (`policy-selector-trigger`), and inactive **Batch Mode** (`batch-scan-toggle` when disabled)—SHALL share a cohesive translucent dark-glass pill treatment over the scanner overlay backdrop rather than rendering **Destination Policy** as a solid white high-contrast button, reserving primary accent fill exclusively for active scanner toggle states (such as enabled **Batch Mode** or active **Flash**).

#### Scenario: User opens scanner and views top bar

- **WHEN** the user opens `/scan` on a mobile or desktop viewport
- **THEN** the top bar displays localized titles, the compact single-line control row with Format (`format-selector-trigger`), Destination Policy (`policy-selector-trigger`: "Shelf", "Wishlist", "Catalog Only"), and Batch Mode (`batch-scan-toggle`) with zero horizontal icon clipping
- **AND** the unified search input (`unified-lookup-input`) spans 100% of the available container width below the control row

#### Scenario: Destination policy pill harmonizes visually with sibling TopBar controls

- **WHEN** the scanner top bar renders with `format-selector-trigger`, `policy-selector-trigger`, and an inactive `batch-scan-toggle`
- **THEN** `policy-selector-trigger` uses the same translucent dark-glass pill styling (`bg-white/10`, white text, subtle translucent border, translucent hover state) as `format-selector-trigger` instead of a solid white (`bg-white` / `text-black`) fill
- **AND** text and chevron icon contrast remain clearly legible against the dark overlay backdrop across both mobile (`390x844`) and desktop (`1280x800`) viewports

#### Scenario: User changes policy mode

- **WHEN** the user opens the Destination Policy selector (`policy-selector-trigger`) and selects "Catalog Only", "Wishlist", or "Shelf"
- **THEN** the active policy pill updates immediately, displays localized guidance, and persists across scans without ambiguous terminology

#### Scenario: User switches media format via compact selector menu

- **WHEN** the user activates the Format selector pill (`format-selector-trigger`)
- **THEN** a localized menu opens displaying every registered format in `SCAN_FORMATS` with icon and full label
- **AND** selecting a format updates the active pill label immediately and closes the menu

### Requirement: Single call to action on disambiguation sheet

The disambiguation sheet SHALL display clean candidate cards with clear one-tap selection targets and localized strings. Secondary links and redundant metadata tags SHALL NOT clutter the view.

#### Scenario: User views candidate cards on disambiguation sheet

- **WHEN** the disambiguation sheet renders candidate cards
- **THEN** each candidate card presents a clean, unambiguous tap target to select the desired candidate

### Requirement: Zero-refetch metadata passing

The scanner capture pipeline SHALL retain initial scan metadata in component state upon a successful scan and pass it directly to the success card to prevent redundant network fetches.

#### Scenario: Successful scan transition to success card

- **WHEN** a scan is successfully processed in camera capture
- **THEN** the initial scan metadata (title, creator, format, cover_url, work_id, manifestation_id) is passed as props directly to the success card without triggering a GET /api/manifestations/<id> request

### Requirement: Non-occluding mobile scanner feedback notifications

The system SHALL position feedback notifications (toasts) on mobile viewports (< 640px) at `top-center` so they do not collide with, overlap, or obstruct the fixed bottom navigation bar (`[Home | Collection | Scan | Profile]`).

#### Scenario: User adds item on mobile device

- **WHEN** the user adds an item to their collection or wishlist on a mobile screen width (< 640px)
- **THEN** the confirmation toast appears at the top-center of the viewport and the 4 bottom navigation buttons remain completely visible and interactive

### Requirement: Continuous batch scanning and camera auto-start

The system SHALL support continuous batch scanning by automatically activating the camera scanner when navigating back to the scanner interface within an active ingestion workflow.

#### Scenario: User returns to scanner after adding item

- **WHEN** the user adds an item to their collection and then navigates to `/scan` via the bottom navigation bar or top bar
- **THEN** the camera scanner activates automatically without requiring a manual tap on the camera activation control

#### Scenario: User scans an item already in collection

- **WHEN** the user scans an item that is already present in their collection
- **THEN** the success card displays both a "View in Collection" action and a "Scan another" action
- **AND** navigating to the item detail page preserves the continuous scanning intent for subsequent scanner navigation

#### Scenario: User clicks scan another on success card

- **WHEN** the user clicks "Scan another" on the success card
- **THEN** the card is dismissed and the camera scanner immediately re-engages in barcode scanning mode

### Requirement: Streamlined two-tab scanner bottom sheet without duplicate search

The scanner bottom sheet SHALL present two capture mode tabs (`Barcode` and `Snap Cover`), removing the duplicate `Manual Search` tab while retaining a direct secondary `Enter details manually` fallback trigger (`enter-manually-link`) and automatic manual-entry fallback on lookup failure/timeout.

#### Scenario: User views the bottom sheet capture tabs and triggers manual entry

- **WHEN** the user views the scanner bottom sheet
- **THEN** only `Barcode` (`scanner-tab-barcode`) and `Snap Cover` (`scanner-tab-cover`) tabs are displayed (`scanner-tab-manual` is absent)
- **AND** activating `enter-manually-link` opens `ManualEntryForm` directly without requiring an intermediate search input inside the sheet
