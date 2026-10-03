# item-lending-tracking Specification

## Purpose

Specify lending of physical media: borrow requests against an Item with duplicate and self-borrowing refusal, resolution that updates the Item's custody state and writes an ItemStatusLog entry, owner-scoped request listing, per-Item status lookup, and a test-reset endpoint that fails closed.

## Requirements

### Requirement: Loan requests are recorded against a physical Item

A borrow request MUST be recorded against a specific physical Item, and MUST be
refused for a user borrowing their own item.

#### Scenario: A user requests to borrow another user's available item

- **WHEN** an authenticated user posts a loan request for an Item they do not own
  and whose `collection_status` is `available`
- **THEN** a pending `LoanRequest` is recorded against that Item
- **AND** the response identifies the request

#### Scenario: A user requests to borrow their own item

- **WHEN** an authenticated user posts a loan request for an Item they own
- **THEN** the request is refused with a client error
- **AND** no `LoanRequest` is recorded

#### Scenario: A user requests an item that is not available

- **WHEN** a loan request is posted for an Item whose `collection_status` is
  anything other than `available`
- **THEN** the request is refused with a client error

#### Scenario: A user submits a second request for the same item

- **WHEN** a user already has a pending loan request for an Item
- **AND** they post another request for the same Item
- **THEN** the second request is refused with 409 Conflict
- **AND** the existing pending request is left untouched

### Requirement: Loan request resolution updates the Item's custody state

Resolving a pending request MUST set the Item's `collection_status` to `lent` and
write an `ItemStatusLog` entry, so the change is visible in the FRBR custody
timeline rather than only in the request table.

#### Scenario: An owner approves a pending request

- **WHEN** the owner of the Item resolves a pending loan request as approved
- **THEN** the request status becomes `approved`
- **AND** the Item's `collection_status` becomes `lent`
- **AND** an `ItemStatusLog` entry is written recording the transition

#### Scenario: The Item has already left the `lent` state

- **WHEN** a loan request that is no longer pending is resolved
- **THEN** the resolution is refused with a client error
- **AND** the Item's custody state is not modified

#### Scenario: A non-owner attempts to resolve a request

- **WHEN** a user who does not own the Item attempts to resolve its loan request
- **THEN** the resolution is refused as forbidden

### Requirement: Owners can list the pending requests for their items

An owner MUST be able to retrieve the pending loan requests raised against Items
they own, and the listing MUST NOT disclose requests against other users' Items.

#### Scenario: An owner lists pending requests

- **WHEN** the owner requests their loan requests
- **THEN** only pending requests against Items they own are returned

#### Scenario: A user lists loan requests

- **WHEN** a user requests loan requests
- **THEN** they see requests for their own Items
- **AND** requests against Items owned by other users are excluded

### Requirement: Loan status is queryable per Item

The current loan status of an Item MUST be queryable directly.

#### Scenario: A user reads an Item's loan status

- **WHEN** a request is made for an Item's loan status
- **THEN** the response reports that Item's current lending state

#### Scenario: A user marks an Item as lent

- **WHEN** a user marks an Item as lent, naming a borrower
- **THEN** the Item's lending state and borrower are recorded

#### Scenario: An Item transitions away from `lent`

- **WHEN** an Item leaves the `lent` state
- **THEN** the recorded borrower is cleared

### Requirement: The lending test-reset endpoint fails closed

The endpoint that clears lending state for automated tests MUST refuse to run
outside a testing context, MUST require a configured shared secret, and MUST
remain blocked in production even when a secret matches.

#### Scenario: The reset endpoint is called without a configured secret

- **WHEN** the reset endpoint is called and no secret is configured
- **THEN** it refuses, rather than defaulting to allowing the call

#### Scenario: The reset endpoint is called with the wrong secret

- **WHEN** the reset endpoint is called with a secret that does not match
- **THEN** it refuses with 403

#### Scenario: The reset endpoint is called in production

- **WHEN** the reset endpoint is called with the correct secret but the
  application is running in production
- **THEN** it still refuses with 403
