# tag-taxonomy-management Specification

## Purpose

Define the global tag namespace and its aggregation: one tag per name rather than per user, ItemTag links recording who applied the tag, hidden Items excluded from taxonomy counts, and normalized cache keys for taxonomy payloads.

## Requirements

### Requirement: Tags are a single global namespace

Tags MUST be global rather than per-user, so the same name always refers to the
same tag regardless of who created it.

#### Scenario: Two users apply the same tag name

- **WHEN** one user creates a tag named `sci-fi`
- **AND** another user independently applies `sci-fi`
- **THEN** both resolve to the one tag record with that name

#### Scenario: A tag name collides with an existing tag

- **WHEN** a user creates a tag whose name already exists
- **THEN** the existing tag is returned rather than a duplicate being created

### Requirement: An ItemTag link records who applied the tag

The association between an Item and a tag MUST record which user applied it, so
tag provenance survives and per-user removal is possible.

#### Scenario: A user tags an Item

- **WHEN** a user applies a tag to an Item
- **THEN** an `ItemTag` link is created recording both the tag and the user

#### Scenario: A user removes a tag they applied

- **WHEN** a user removes a tag they applied to an Item
- **THEN** the link is removed
- **AND** tags applied by other users to the same Item are unaffected

#### Scenario: A tag is deleted

- **WHEN** a tag is deleted
- **THEN** its Item links are removed with it rather than left dangling

### Requirement: Hidden items are excluded from taxonomy aggregation

Taxonomy and facet counts MUST exclude hidden Items, so an owner hiding part of
their collection does not silently change the shared vocabulary presented to
everyone else.

#### Scenario: An owner hides an Item that carried tags

- **WHEN** an owner marks a tagged Item hidden
- **THEN** that Item's tags do not contribute to taxonomy counts

#### Scenario: A wishlist entry is hidden

- **WHEN** a virtual wishlist entry marked hidden is excluded from aggregation
- **THEN** its tags do not contribute to taxonomy counts

### Requirement: Taxonomy payloads are served from a normalized cache

The taxonomy payload MUST be cached under a key that does not vary with caller
identity or request ordering, and MUST be invalidated by the refresh task.

#### Scenario: Two equivalent taxonomy requests are made

- **WHEN** the same taxonomy is requested in a form that normalizes to the same
  cache key
- **THEN** both are served from one cache entry

#### Scenario: The refresh task runs

- **WHEN** the taxonomy refresh task executes
- **THEN** the cached taxonomy payload is invalidated
