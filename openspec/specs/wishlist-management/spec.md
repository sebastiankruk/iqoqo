# Wishlist Management

## Purpose

Requirements and specifications for wishlist item actions, state reflections, and tagging.

## Requirements

### Requirement: Wishlist State Reflection

The system SHALL reflect when an item is already on the user's wishlist and prevent duplicate additions while providing a path to view the wishlist item.

#### Scenario: Manifestation already on wishlist

- **WHEN** a user views a manifestation that is already on their wishlist
- **THEN** the UI does not offer "Add to Wishlist" and instead provides a button/link to navigate to the virtual wishlist Item.

### Requirement: Wishlist Item Tagging

The system SHALL allow users to apply tags to items that are in a wishlist state.

#### Scenario: Adding a tag to a wishlist item

- **WHEN** a user adds a tag to their wishlist item
- **THEN** the tag is saved and displayed on the wishlist item, just like it would be for a collection item.

### Requirement: Contextual Wishlist Actions Visibility

The system SHALL ensure that wishlist management actions (such as removing an item from the wishlist via the quick-action toggle) are only accessible to the authenticated owner of the collection.

#### Scenario: Unauthenticated user views shared wishlist item

- **WHEN** an unauthenticated user views an item card for a wishlist item on a shared public page
- **THEN** the system SHALL NOT render the actionable removal toggle (Heart icon) or any duplicate state indicators.

#### Scenario: Authenticated user views their own wishlist item

- **WHEN** the authenticated owner views an item card for their own wishlist item
- **THEN** the system SHALL render the actionable removal toggle to allow quick deletion.
