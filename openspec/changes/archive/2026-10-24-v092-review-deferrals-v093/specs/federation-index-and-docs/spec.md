## MODIFIED Requirements

### Requirement: Federated Instance Directory Index
The system MUST support a read-only directory index view listing verified peer libraries from the Federation Trust Graph, displaying instance metadata, total public item counts, and federation endpoints, and MUST degrade gracefully when S2S federation is disabled on the local instance.

#### Scenario: User visits directory index of connected libraries

- **GIVEN** an instance configured with `FEDERATION_DIRECTORY_ENABLED=true`
- **WHEN** a visitor navigates to `/federation/directory` or views the instance index
- **THEN** the system lists active connected peer libraries with their instance icons, descriptions, and public item counts
- **AND** private user collections and non-consented entities remain excluded

#### Scenario: User visits directory index when federation is disabled on the local node

- **GIVEN** an instance where `FEDERATION_ENABLED` is `false`
- **WHEN** a visitor navigates to `/federation/directory`
- **THEN** the page still displays the local instance overview card (`GET /api/v1/public/federation/instance-info`) alongside a friendly notice that S2S federation is currently disabled, rather than failing with a raw HTTP error banner
