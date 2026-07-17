# mobile-facet-drawer Specification

## Purpose
TBD - created by archiving change faceted-navigation-finalization. Update Purpose after archive.
## Requirements
### Requirement: Mobile viewports display a floating filter pill trigger

On viewports narrower than the `lg` Tailwind breakpoint, the sidebar facet panel SHALL be hidden. Instead, a floating pill button anchored to the bottom center of the viewport SHALL be rendered to serve as the facet filter trigger.

#### Scenario: Floating pill renders on mobile

- **WHEN** the viewport width is below the `lg` breakpoint (1024px)
- **THEN** the sidebar filters SHALL be hidden
- **AND** a floating "Filter Library" pill button SHALL be visible at the bottom center of the screen
- **AND** if any filters are active, the pill SHALL display the active filter count as a badge

#### Scenario: Floating pill opens bottom drawer

- **WHEN** the user taps the floating filter pill
- **THEN** a bottom sheet drawer SHALL slide up from the bottom of the viewport
- **AND** the drawer SHALL contain all facet groups rendered by `SidebarFilters`

#### Scenario: Drawer closes on swipe-down

- **WHEN** the user swipes the bottom sheet drawer downward
- **THEN** the drawer SHALL dismiss smoothly

#### Scenario: Drawer closes on backdrop tap

- **WHEN** the bottom sheet drawer is open and the user taps outside the drawer area
- **THEN** the drawer SHALL close

#### Scenario: No Apply button required

- **WHEN** the user toggles a facet inside the mobile drawer
- **THEN** the results grid SHALL update immediately without requiring an "Apply Filters" button press

### Requirement: Mobile drawer uses swipe-to-dismiss (vaul-backed Shadcn Drawer)

The mobile filter drawer SHALL use the Shadcn `<Drawer>` component (backed by vaul) to provide native swipe-to-dismiss behavior and smooth slide-up animation.

#### Scenario: Drawer height is bounded

- **WHEN** the mobile drawer is opened
- **THEN** the drawer content area SHALL have a maximum height of 80% of the viewport height (`h-[80vh]`)
- **AND** the facet list inside SHALL be independently scrollable

