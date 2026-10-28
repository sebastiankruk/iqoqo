## Purpose
Multi-agent review sweep across 0.9.x, documentation completion, and verification of mobile app discovery/auth contract.

## ADDED Requirements

### Requirement: Mobile Client Discovery & Auth Contract

The API SHALL support dynamic server discovery and PAT/JWT session bootstrap workflows required by mobile apps.

#### Scenario: Mobile client discovers server capabilities
- **WHEN** A mobile client queries /.well-known/nodeinfo and /api/auth/providers
- **THEN** Returns supported auth strategies, software version, and CORS headers.

### Requirement: Complete Core Domain & Operational Test Coverage

The testing harness SHALL provide isolated test coverage for backend ontology guards, federation enablement decorators, custodian lending dashboards, and administrative data maintenance scripts.

#### Scenario: Runtime expansion aggregation guard test
- **WHEN** `validate_work_not_expansion_aggregated` is invoked with a Work linked via `iqoqo:is_expansion_of`
- **THEN** it raises a `ValueError` preventing aggregation into container works.

#### Scenario: Federation disabled guard returns 404
- **WHEN** an incoming ActivityPub or federation request targets a `@federation_required` view while `FEDERATION_ENABLED=False`
- **THEN** the decorator returns `404 Not Found` without routing into federation handlers.

#### Scenario: Admin lending dashboard component test
- **WHEN** a custodian visits `/admin/lending`
- **THEN** pending loan requests render and approve/reject actions invoke `useResolveLoan` mutations.

