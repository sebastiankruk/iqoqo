# scanner-ux-streamline Specification

## Purpose

Streamlines the scanner user experience with clear policy naming ("Shelf" / "Wishlist" / "Catalog Only"), full TopBar localization, clean single-tap candidate selection, zero-refetch metadata passing, and preserved counter-rotating waiting animations.

## Requirements

### Requirement: Localized scanner top bar and clear policy naming

The scanner top bar SHALL display localized media format options and policy selectors. The policy selector SHALL use clear, unambiguous naming ("Shelf" for inventory, "Wishlist", and "Catalog Only" for cataloging) with localized descriptive guidance. All top bar headers, labels, and tooltips SHALL be fully translated in both English and Polish.

#### Scenario: User opens scanner and views top bar

- **WHEN** the user opens the scanner interface
- **THEN** the top bar displays localized titles, format selectors, and policy options ("Shelf", "Wishlist", "Catalog Only") matching the active locale

#### Scenario: User changes policy mode

- **WHEN** the user selects "Catalog Only" or "Shelf" in the top bar
- **THEN** the active policy is highlighted and the policy state persists across scans without ambiguous terminology

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
