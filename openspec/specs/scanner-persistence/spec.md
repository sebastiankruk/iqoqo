# scanner-persistence Specification

## Purpose
TBD - created by archiving change scanner-ux-policy-scanning. Update Purpose after archive.
## Requirements
### Requirement: Media Type Selection Persistence

The scanner UI SHALL remember the user's last selected media type and restore it across consecutive scan operations and page reloads.

#### Scenario: Sequential scanning of same media type

- **WHEN** a user selects `"music"` as the media type and successfully scans a barcode
- **THEN** the scanner UI SHALL retain `"music"` as the selected media type for the next scan.

#### Scenario: Persistence across page navigation

- **WHEN** a user selects `"video"` as the media type, navigates to the dashboard, and returns to the scanner
- **THEN** the scanner UI SHALL initialize with `"video"` selected instead of the system default.

### Requirement: Policy Selection Persistence

The scanner UI SHALL remember the user's last selected scanning policy (Inventory, Wishlist, Catalog) and restore it.

#### Scenario: Sequential wishlist scanning

- **WHEN** a user selects the "Add to Wishlist" policy and scans an item
- **THEN** the UI SHALL retain the "Add to Wishlist" policy for the next scan, preventing accidental inventory additions.

