## ADDED Requirements

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
