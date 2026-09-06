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
