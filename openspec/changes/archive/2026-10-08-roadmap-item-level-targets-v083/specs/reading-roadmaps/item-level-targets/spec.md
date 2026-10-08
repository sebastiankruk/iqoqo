## Purpose

Reading-roadmap entries identify the FRBR-level target a user intends to read, from an abstract title through a particular owned physical copy. This capability defines exclusive four-level targeting, ownership boundaries, user-visible target identity, and safe lifecycle behavior.

## ADDED Requirements

### Requirement: A roadmap entry targets exactly one FRBR level

The system SHALL require every roadmap entry to reference exactly one of Work, Expression, Manifestation, or Item. Work identifies a title independent of a selected realization or edition; Expression identifies a particular realization such as a translation; Manifestation identifies a specific edition/embodiment, often identifiable by ISBN; Item identifies one actual individual copy.

#### Scenario: Create a Work target
- **WHEN** a user adds an entry with only `work_id`
- **THEN** the roadmap entry targets that Work and the other three target references are null

#### Scenario: Create an Expression target
- **WHEN** a user adds an entry with only `expression_id`
- **THEN** the roadmap entry targets that Expression and the other three target references are null

#### Scenario: Create a Manifestation target
- **WHEN** a user adds an entry with only `manifestation_id`
- **THEN** the roadmap entry targets that Manifestation and the other three target references are null

#### Scenario: Create an Item target
- **WHEN** a user adds an entry with only `item_id`
- **THEN** the roadmap entry targets that individual Item and the other three target references are null

#### Scenario: Reject missing or ambiguous targets
- **WHEN** a create or target-replacement request supplies no target reference or more than one of `work_id`, `expression_id`, `manifestation_id`, and `item_id`
- **THEN** the API rejects the request with a client validation error and does not persist or alter an entry

#### Scenario: Database rejects invalid target cardinality
- **WHEN** a persistence operation attempts to store a roadmap entry with zero or multiple non-null FRBR target references
- **THEN** the database rejects it through the roadmap target integrity constraint

### Requirement: Item targets are real copies owned by the roadmap user

An Item roadmap target SHALL identify an existing physical Item record whose owner is the authenticated owner of the roadmap. A wishlist intent, a borrowed Item owned by another user, a missing ID, or a fabricated/placeholder record SHALL NOT qualify as an Item target. Ownership is determined by the Item's owner relationship; this requirement does not depend on whether the owner's copy is currently lent out.

#### Scenario: Select an owned physical copy
- **WHEN** a user searches for Item targets
- **THEN** the selector offers only actual Item records owned by that user and shows enough catalog context to distinguish the selected copy from its Manifestation

#### Scenario: Reject a borrowed or another user's copy
- **WHEN** a user attempts to add or replace a roadmap target with an Item owned by another user, including an Item merely borrowed by the requester
- **THEN** the API returns a not-found response without revealing the other user's Item details and leaves the roadmap unchanged

#### Scenario: Reject a nonexistent or virtual wishlist ID
- **WHEN** a user submits an Item target ID that does not identify a physical Item row, including a negative virtual wishlist ID
- **THEN** the API rejects it as not found and creates no roadmap entry

### Requirement: Roadmap API creates, reads, updates, and deletes target entries

The authenticated roadmap API SHALL accept any one of the four target identifiers when creating an entry, return the selected target in roadmap reads, allow replacing an entry's target with exactly one valid target, and allow deleting an individual roadmap entry without deleting its target entity or containing roadmap. Existing roadmap ownership, sequencing, notes, dates, status, and reorder behavior SHALL remain intact unless the caller explicitly removes an entry.

#### Scenario: Read target identity in roadmap serialization
- **WHEN** a user fetches their roadmap list
- **THEN** each entry includes nullable `work_id`, `expression_id`, `manifestation_id`, and `item_id` fields with exactly one populated, plus an explicit target-level discriminator and human-readable target summary

#### Scenario: Replace a target while preserving entry state
- **WHEN** the roadmap owner replaces an entry target with exactly one valid target at any of the four FRBR levels
- **THEN** the entry points only to the new target while its position, status, notes, target date, and completion timestamp are preserved

#### Scenario: Delete an individual roadmap entry
- **WHEN** the roadmap owner deletes one entry
- **THEN** only that roadmap entry is removed, its former target remains unchanged, and the remaining entries retain their relative order with positions compacted

#### Scenario: Reject mutation by a non-owner
- **WHEN** a caller attempts to create an entry in, replace a target on, reorder, or delete an entry belonging to another user's roadmap
- **THEN** the API returns not found and makes no change

### Requirement: Roadmap UI explains and distinguishes all target levels

The roadmap UI SHALL let users choose one target level and search/select an entity at that level. It SHALL label the level and present enough context to distinguish the abstract Work, its Expression, its Manifestation/edition, and an individual Item copy. Item selection SHALL be sourced from owned physical Items, not wishlist intentions or borrowed copies.

#### Scenario: Choose a Work-level title
- **WHEN** a user selects Work as the target level
- **THEN** the chooser allows selecting a title without requiring an edition or realization

#### Scenario: Choose an Expression or Manifestation
- **WHEN** a user selects Expression or Manifestation as the target level
- **THEN** the chooser identifies the realization/translation or specific edition respectively, rather than silently converting it to the Work target

#### Scenario: Display a particular copy
- **WHEN** a roadmap entry targets an Item
- **THEN** its card visibly identifies it as an Item/copy and includes associated title and edition context so it is not presented as merely another Work or Manifestation target

### Requirement: Deleting a referenced FRBR target is restricted

The system SHALL preserve roadmap target identity and entry data when a referenced Work, Expression, Manifestation, or Item is deleted. It SHALL prevent deletion of a referenced target until the roadmap entry is explicitly removed, and the owning API SHALL report a conflict rather than silently nulling the target or deleting roadmap progress.

#### Scenario: Prevent deletion of a target in use
- **WHEN** a catalog or inventory deletion attempts to remove a target referenced by a roadmap entry
- **THEN** the database prevents the deletion, the roadmap entry and roadmap remain unchanged, and the API reports a conflict

#### Scenario: Delete target after removing its roadmap entry
- **WHEN** the roadmap owner removes the entry and then deletes its former target
- **THEN** the target can be deleted and the roadmap itself and unrelated entries remain intact

### Requirement: Purchase intentions do not create Item targets

The system SHALL NOT create a physical Item row solely to represent a planned purchase or an unowned desired copy. A roadmap intention without a specific owned copy SHALL target the appropriate Work or Manifestation; wishlist intent SHALL continue to use wishlist intent records rather than placeholder Item records.

#### Scenario: Plan to read a title not yet owned
- **WHEN** a user wants to plan a title without owning a physical copy
- **THEN** the roadmap can target its Work (or a chosen Manifestation where an edition is intended) without creating an Item row

#### Scenario: A physical copy is added later
- **WHEN** the user later acquires and records an actual copy
- **THEN** the user can replace the roadmap target with that real owned Item without retroactively creating a placeholder copy
