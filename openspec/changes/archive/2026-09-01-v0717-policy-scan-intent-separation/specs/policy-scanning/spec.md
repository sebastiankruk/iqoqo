## MODIFIED Requirements

### Requirement: Policy-Based Scanner Resolution

The system SHALL accept a `policy` attribute in scanner resolution requests to dictate whether the scan results in physical inventory, a wishlist intent, or purely catalog metadata.

#### Scenario: Scan with inventory policy

- **WHEN** a user submits a scan with `policy: "inventory"` (or omitted policy)
- **THEN** the system SHALL resolve the FRBR metadata AND instantiate an `Item` record linked to the user's collection.

#### Scenario: Scan with wishlist policy

- **WHEN** a user submits a scan with `policy: "wishlist"`
- **THEN** the system SHALL resolve the FRBR metadata AND create a `UserWorkIntent` (status `wish_list`) linked to the user, BUT SHALL NOT instantiate an `Item` record.

#### Scenario: Scan with catalog_only policy

- **WHEN** a user submits a scan with `policy: "catalog_only"`
- **THEN** the system SHALL resolve the FRBR metadata into the global catalog (Work/Expression/Manifestation) BUT SHALL NOT link any user-specific `Item` or `UserWorkIntent`.
