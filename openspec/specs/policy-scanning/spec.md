# policy-scanning Specification

## Purpose

Define scanner ingestion policies to dictate whether scanned items resolve into physical inventory, user wishlist intents, or purely global catalog metadata.

## Requirements
### Requirement: Policy-Based Scanner Resolution

The system SHALL accept a `policy` attribute in scanner resolution requests to dictate whether the scan results in physical inventory, a wishlist intent, or purely catalog metadata.

#### Scenario: Scan with inventory policy

- **WHEN** a user submits a scan with `policy: "inventory"` (or omitted policy)
- **THEN** the system SHALL resolve the FRBR metadata AND instantiate an `Item` record linked to the user's collection.

#### Scenario: Scan with wishlist policy

- **WHEN** a user submits a scan with `policy: "wishlist"`
- **THEN** the system SHALL resolve the FRBR metadata AND create a `UserWorkIntent` (status `wish_list`) linked to the user, BUT SHALL NOT instantiate an `Item` record.

#### Scenario: Scan with catalog or catalog_only policy

- **WHEN** a user submits a scan with `policy: "catalog"` or `policy: "catalog_only"`
- **THEN** the system SHALL resolve the FRBR metadata into the global catalog (Work/Expression/Manifestation) BUT SHALL NOT link any user-specific `Item` or `UserWorkIntent`.

### Requirement: Scanner Response Polymorphism

The scanner API SHALL return context-aware responses based on the executed policy so the frontend can display appropriate success messages.

#### Scenario: Returning non-item entities

- **WHEN** a scan executes with a non-inventory policy
- **THEN** the API response SHALL include the resolved `Manifestation` data and indicate the action taken (e.g., `"action": "added_to_wishlist"` or `"action": "cataloged"`).
