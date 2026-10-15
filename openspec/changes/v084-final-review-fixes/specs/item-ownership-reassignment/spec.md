## MODIFIED Requirements

### Requirement: Ownership reassignment is restricted to authorized administrators

The system SHALL permit Item ownership reassignment to an authenticated user who has either the `admin` role, `custodian` role, or `contributor` role with item transfer privileges (`transfer:item` / `write:users`). Source/target account discovery SHALL enforce SQL-level pagination and bounds (`limit`/`offset`/query filtering) rather than unbounded table dumps, and SHALL require appropriate account read authorization (`read:users` or `transfer:item`). Ordinary owners, borrowers, users with only `update:item` or `write:item`, and callers without authentication SHALL NOT use reassignment operations. Reassignment affordances SHALL be accessible within administrator and custodian navigation surfaces for users holding any of the authorized roles (`admin`, `custodian`, or `contributor`).

#### Scenario: Authorized administrator opens reassignment

- **WHEN** an authenticated administrator with `write:users` requests the reassignment UI or API
- **THEN** the system permits the operation subject to source, target, and scope validation

#### Scenario: Authorized custodian opens reassignment

- **WHEN** an authenticated custodian or contributor with transfer permissions requests the reassignment UI or API
- **THEN** the system permits the operation subject to source, target, and scope validation and displays the reassignment option in the navigation menu

#### Scenario: Account discovery enforces pagination bounds

- **WHEN** an authorized user queries the ownership account discovery endpoint
- **THEN** the system executes bounded SQL queries with limit and search constraints and returns paginated accounts without dumping the entire user directory into memory.

#### Scenario: Administrator without account-read permission requests account discovery

- **WHEN** an authenticated administrator with `write:users` but without `read:users` requests source or target account discovery
- **THEN** the system denies account discovery without exposing account identities, while reassignment authorization remains independently enforced

#### Scenario: Non-admin with user-write permission attempts reassignment

- **WHEN** an authenticated user who has neither `admin` nor `custodian` role has `write:users` and submits a reassignment request
- **THEN** the system denies the request and changes no Item or custody data

#### Scenario: Ordinary owner attempts self-service ownership override

- **WHEN** an ordinary user submits `owner_id` through the Item update API or invokes an ownership-reassignment operation
- **THEN** the system rejects the ownership change and leaves the Item unchanged
