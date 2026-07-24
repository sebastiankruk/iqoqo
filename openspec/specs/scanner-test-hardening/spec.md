## ADDED Requirements

### Requirement: Bottom-sheet component has unit test coverage
The `bottom-sheet.tsx` component SHALL have unit tests covering tab switching behavior, barcode scan loop, manual search text input with lookup API call, error display, and manual entry fallback button. All tests SHALL use mocked browser APIs.

#### Scenario: Bottom-sheet renders three tabs
- **WHEN** bottom-sheet renders with default state
- **THEN** three tab buttons SHALL be visible: barcode, snap cover, and manual search

#### Scenario: Tab switching changes active content
- **WHEN** user clicks the "Manual Search" tab
- **THEN** the manual search text input SHALL be visible and the camera viewfinder SHALL be hidden

#### Scenario: Manual search triggers lookup on submit
- **WHEN** user types an identifier and presses enter
- **THEN** the lookup API SHALL be called with the search text and a loading state SHALL be displayed

#### Scenario: Barcode scan renders camera viewfinder
- **WHEN** the barcode tab is active
- **THEN** the camera viewfinder component SHALL be rendered

### Requirement: Top-bar component has unit test coverage
The `top-bar.tsx` component SHALL have unit tests covering format selector rendering, policy selector rendering, flash toggle button, and back-link with cancel callback.

#### Scenario: Top-bar renders format selector with all scan formats
- **WHEN** top-bar renders
- **THEN** a format selector dropdown SHALL be visible with options for all supported scan formats

#### Scenario: Policy selector changes active policy
- **WHEN** user selects "Wishlist" from the policy selector
- **THEN** the policy state SHALL update to "wishlist" and the success card SHALL adapt

#### Scenario: Back-link invokes cancel callback
- **WHEN** user clicks the back-link
- **THEN** the cancel callback SHALL be invoked

### Requirement: Camera-capture component tests all upload modes
The `camera-capture.tsx` component SHALL have unit tests for all three upload modes: cover upload, gallery upload, and vision extraction with polling. Tests SHALL cover file input handling, drag-and-drop, confirmation dialog, and error handling.

#### Scenario: Cover mode uploads file and calls cover endpoint
- **WHEN** a file is selected in cover upload mode
- **THEN** the file SHALL be uploaded to the manifestation cover endpoint and a success toast SHALL appear

#### Scenario: Gallery mode uploads file and calls images endpoint
- **WHEN** a file is selected in gallery upload mode
- **THEN** the file SHALL be uploaded to the manifestation images endpoint

#### Scenario: Vision mode submits file and polls for result
- **WHEN** a file is selected in vision extraction mode
- **THEN** the file SHALL be submitted to the vision extract endpoint and the component SHALL poll until a result is returned

#### Scenario: Drag-and-drop triggers file upload in cover mode
- **WHEN** a file is dropped on the camera-capture drop zone
- **THEN** the file SHALL be processed as if selected via file input

### Requirement: Scanner strategies have unit tests for all media types
The scanner strategy module SHALL have unit tests for `AudioLookupStrategy`, `VideoLookupStrategy`, and `PuzzleLookupStrategy` in addition to the existing `BookLookupStrategy` and `BoardGameLookupStrategy` tests.

#### Scenario: Audio lookup strategy delegates to Discogs
- **WHEN** `AudioLookupStrategy` is invoked with a UPC barcode
- **THEN** the Discogs metadata fetcher SHALL be called

#### Scenario: Video lookup strategy delegates to TMDB
- **WHEN** `VideoLookupStrategy` is invoked with an EAN barcode
- **THEN** the TMDB metadata fetcher SHALL be called

### Requirement: E2E scanner workflow validates end-to-end scan flow
An E2E test SHALL validate the scanner workflow: navigate to `/scan`, select format, tap barcode scan tab, detect a barcode, display disambiguation sheet, select candidate, and add to library.

#### Scenario: Full scanner E2E flow
- **WHEN** user navigates to `/scan`, selects "Book" format, and a barcode is detected
- **THEN** a disambiguation sheet SHALL appear with candidates, the user SHALL select one, a success card SHALL display, and "Add to Library" SHALL create the item

### Requirement: E2E policy scanning validates policy switcher behavior
An E2E test SHALL validate the scanner's policy switching: selecting "Wishlist" or "Catalog" in the top-bar changes how the success card renders and which API endpoint is called.

#### Scenario: Wishlist policy creates wishlist item
- **WHEN** user selects "Wishlist" policy, scans a barcode, and adds the item
- **THEN** the item SHALL be created with wishlist intent and no item_id

#### Scenario: Catalog policy creates catalog-only entry
- **WHEN** user selects "Catalog" policy, scans a barcode, and adds the item
- **THEN** the item SHALL be created as a catalog entry without intent_id or item_id
