# user-work-intent-wishlist Specification

## Purpose
Specify user work intent (wishlist/to-read/to-watch) tracking, intent status transitions, and virtual item boundaries.

## Requirements

### Requirement: Polymorphic Media Disambiguation for Wishlist Items
The system SHALL expose `work_type` and `expression.medium_type` in UserWorkIntent responses and visually disambiguate non-book entities (e.g. Vinyl, Audiobook, BoardGame) via distinct media badges in the wishlist and roadmap UI.

#### Scenario: Vinyl record rendered in wishlist
- **WHEN** a UserWorkIntent response includes `work_type` "AudioWork" and `medium_type` "Vinyl"
- **THEN** the UI correctly displays a Music/Audio badge rather than defaulting to a generic Book badge

#### Scenario: Board game rendered in wishlist
- **WHEN** a UserWorkIntent response includes `work_type` "GameWork"
- **THEN** the UI correctly displays a BoardGame badge instead of a Book badge
