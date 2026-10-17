## Context

Privacy-by-default is a core iqoqo architectural pillar.

## Goals / Non-Goals

**Goals:**
- Prevent accidental exposure of private collections.
- Provide transparent user-facing federation controls.

**Non-Goals:**
- Retroactive batch privacy toggling of existing items.

## Decisions

### Default to Private
* **Decision**: New accounts default to `private` item visibility and `federated_profile=False`.
* **Rationale**: Strict GDPR / Privacy compliance.

### Just-In-Time Key Generation
* **Decision**: Generate user RSA keypair only when user first enables federation consent.
* **Rationale**: Conserves database storage and CPU cycles for inactive users.

## Risks / Trade-offs

- ('[Risk] User forgets they are private and wonders why friends cannot see items', 'Mitigation: Display clear visibility indicator badges on Item views.')
