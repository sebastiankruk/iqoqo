---
type: Concept
title: spec
timestamp: 2026-07-22T10:18:49Z
---

## ADDED Requirements

### Requirement: Active filter chip row has no visible scrollbar

The horizontal scrolling container for active filter chips MUST NOT display a visible scrollbar on any platform (desktop, mobile). Scroll functionality SHALL remain available via trackpad gestures, touch swipe, or shift-scroll.

#### Scenario: Desktop browser hides scrollbar

- **WHEN** the active filter chip row contains more chips than fit the viewport width
- **THEN** the container SHALL scroll horizontally without rendering a visible scrollbar
- **AND** the user SHALL still be able to scroll using trackpad gestures or shift+scroll wheel

#### Scenario: Mobile browser hides scrollbar

- **WHEN** the active filter chip row is viewed on a mobile device
- **THEN** the container SHALL scroll horizontally via touch swipe without rendering a visible scrollbar

### Requirement: Mobile filter trigger uses secondary visual weight

The floating filter pill on mobile viewports MUST be styled as a secondary action to avoid competing with the primary Add/Scan FAB for user attention. It SHALL use a translucent, blurred background treatment (glassmorphism) rather than a solid, high-contrast fill.

#### Scenario: Filter pill uses glassmorphism styling

- **WHEN** the mobile filter pill is rendered on screens narrower than the `lg` breakpoint
- **THEN** it SHALL use a translucent dark background with backdrop blur (e.g., `bg-black/80 backdrop-blur-md`) and a subtle border (e.g., `border-white/10`)
- **AND** its visual weight SHALL be lower than any primary action button on the same screen

#### Scenario: Filter pill shows active filter count badge

- **WHEN** the user has one or more active filters
- **THEN** the filter pill SHALL display a numeric badge showing the count of active filters
- **AND** the badge SHALL use a high-contrast style to remain legible against the translucent background

### Requirement: Wishlist view action uses navigational icon

The "View Wishlist Item" dropdown action MUST use an icon that signals navigation/viewing (e.g., an eye icon) rather than reusing the same icon as the "Add to Wishlist" action. This distinction SHALL reduce cognitive friction by clearly differentiating mutation actions from navigation actions.

#### Scenario: View Wishlist uses Eye icon

- **WHEN** a manifestation already has an associated wishlist item
- **AND** the user opens the Add to Collection dropdown
- **THEN** the "View Wishlist Item" action SHALL display an `Eye` icon (not `BookmarkPlus`)

#### Scenario: Add to Wishlist retains BookmarkPlus icon

- **WHEN** a manifestation does NOT have an associated wishlist item
- **AND** the user opens the Add to Collection dropdown
- **THEN** the "Add to Wishlist" action SHALL display the `BookmarkPlus` icon
