# federation-index-and-docs Specification

## Purpose
TBD - created by archiving change federation-index-instance-and-enduser-docs-v09x. Update Purpose after archive.

## Requirements

### Requirement: Federated Instance Directory Index
The system MUST support a read-only directory index view listing verified peer libraries from the Federation Trust Graph, displaying instance metadata, total public item counts, and federation endpoints.

#### Scenario: User visits directory index of connected libraries

- **GIVEN** an instance configured with `FEDERATION_DIRECTORY_ENABLED=true`
- **WHEN** a visitor navigates to `/federation/directory` or views the instance index
- **THEN** the system lists active connected peer libraries with their instance icons, descriptions, and public item counts
- **AND** private user collections and non-consented entities remain excluded

### Requirement: In-App End-User Documentation Hub
The frontend application MUST provide an in-app documentation interface (`/help`) accessible from the main navigation and user menu.

#### Scenario: Collector browses in-app help documentation

- **GIVEN** any authenticated or anonymous user
- **WHEN** the user clicks "Help & Documentation" in the navigation
- **THEN** the in-app documentation hub renders organized guides on barcode scanning, FRBR entity levels, and federated loans
- **AND** articles are searchable and respect the user's active UI locale (`en` / `pl`)
