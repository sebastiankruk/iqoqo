# frbr/item-manifestation-metadata-consistency Specification

## Purpose

Define the consistency requirement between an Item and its parent Manifestation after the parent chain's content type is reclassified.

## Requirements

### Requirement: Item Metadata Does Not Contradict Its Manifestation

After a content-type change on a Work, Expression or Manifestation, the system SHALL NOT report, through any exported or displayed value, a content type or carrier format for an Item that contradicts the reclassified parent Manifestation.

A Manifestation is the structural record of a carrier: `Item` has no carrier column, and any copy of the type or carrier held in `Item.meta` is denormalised. The Manifestation remains authoritative, and synchronization propagates to Item metadata carrier keys on reclassification.

#### Scenario: A reclassified title is exported

- **WHEN** an Expression carrying an Item is reclassified such that the Manifestation's carrier format degrades to the new type's placeholder
- **THEN** an export of that Item reports the carrier and content type of the reclassified Manifestation, not the values held before the change

#### Scenario: An Item's displayed carrier follows the Manifestation

- **WHEN** an Item is displayed after its parent chain has been reclassified
- **THEN** the carrier shown is the Manifestation's, and any copy in the Item's metadata does not override it

#### Scenario: The parent Manifestation is the authority

- **WHEN** the carrier format of a reclassified Manifestation is read
- **THEN** that value is the one used, and it is not recomputed from, or overridden by, any Item beneath it

#### Scenario: Existing rows are already inconsistent

- **WHEN** this requirement is first introduced and Item metadata written before it diverges from its Manifestation
- **THEN** whether those rows are corrected is stated explicitly rather than implied by the change, so that the reported scope of the fix is not wider than what was done
