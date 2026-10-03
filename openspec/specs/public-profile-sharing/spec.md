# public-profile-sharing Specification

## Purpose

Define public catalog exposure: hidden Items excluded from a profile and from its counts, a distinguishable 404 for an unknown user, an inventory-eligibility check that does not enumerate the collection, and explicit, revocable collection sharing.

## Requirements

### Requirement: A public profile exposes only non-hidden Items

A public profile MUST exclude Items the owner has marked hidden, both from the
returned payload and from any count the profile reports.

#### Scenario: An owner hides an Item

- **WHEN** an Item is marked hidden by its owner
- **THEN** it does not appear in the owner's public profile
- **AND** it is excluded from the profile's Item count

#### Scenario: A visitor reads a public profile

- **WHEN** an unauthenticated visitor requests a public profile
- **THEN** the response contains only the owner's non-hidden Items

### Requirement: A profile that does not exist is reported as not found

Requesting a profile for an unknown username MUST return 404 rather than an empty
success response, so a caller can distinguish "no such profile" from "profile
exists but has nothing to show".

#### Scenario: A visitor requests an unknown username

- **WHEN** a visitor requests a profile for a username that does not exist
- **THEN** the response is 404

### Requirement: Inventory availability can be checked without exposing the collection

The inventory check endpoint MUST report whether a user's catalog is suitable for
sharing WITHOUT enumerating the items themselves.

#### Scenario: A user checks their own inventory

- **WHEN** a user runs the inventory check
- **THEN** the response reports an eligibility verdict
- **AND** it does not disclose the items in the collection as part of the check

#### Scenario: A visitor runs the inventory check for another user

- **WHEN** the check is invoked for a user other than the caller
- **THEN** the caller is refused
- **AND** no inventory information is returned

### Requirement: Shared collections are explicit and revocable

Sharing a collection MUST be an explicit, owner-initiated act, and a shared
collection MUST be removable by its owner.

#### Scenario: An owner shares a collection

- **WHEN** an owner creates a shared collection
- **THEN** a shareable collection record is created for that owner

#### Scenario: An owner removes a shared collection

- **WHEN** an owner deletes a shared collection they created
- **THEN** it is no longer listed as shared
- **AND** the previously shared URL no longer resolves to it

#### Scenario: A non-owner lists shared collections

- **WHEN** a user lists shared collections
- **THEN** they see collections that are shared for them to view
- **AND** collections belonging to other owners are not listed as theirs
