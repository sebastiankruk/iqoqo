## MODIFIED Requirements

### Requirement: Ownership reassignment is restricted to authorized administrators

The system SHALL permit Item ownership reassignment to an authenticated user who has either the `admin` role or the `custodian` role, along with the `write:users` permission. Source/target account discovery SHALL additionally require `read:users`. Ordinary owners, borrowers, users with only `update:item` or `write:item`, and callers without authentication SHALL NOT use reassignment operations. Reassignment SHALL NOT be exposed as a public or self-service ownership override, and the ordinary Item update API SHALL continue to reject `owner_id` changes. Reassignment affordances SHALL be accessible within both administrator and custodian navigation surfaces.

#### Scenario: Authorized administrator opens reassignment

- **WHEN** an authenticated administrator with `write:users` requests the reassignment UI or API
- **THEN** the system permits the operation subject to source, target, and scope validation

#### Scenario: Authorized custodian opens reassignment

- **WHEN** an authenticated custodian with `write:users` requests the reassignment UI or API
- **THEN** the system permits the operation subject to source, target, and scope validation and displays the reassignment option in the custodian navigation menu

#### Scenario: Administrator without account-read permission requests account discovery

- **WHEN** an authenticated administrator with `write:users` but without `read:users` requests source or target account discovery
- **THEN** the system denies account discovery without exposing account identities, while reassignment authorization remains independently enforced

#### Scenario: Non-admin with user-write permission attempts reassignment

- **WHEN** an authenticated user who has neither `admin` nor `custodian` role has `write:users` and submits a reassignment request
- **THEN** the system denies the request and changes no Item or custody data

#### Scenario: Ordinary owner attempts self-service ownership override

- **WHEN** an ordinary user submits `owner_id` through the Item update API or invokes an ownership-reassignment operation
- **THEN** the system rejects the ownership change and leaves the Item unchanged
