## ADDED Requirements

### Requirement: Allegro OAuth polling is isolated in E2E verification
The Allegro OAuth E2E verification tests SHALL intercept the Allegro authentication polling endpoint and return a deterministic mock response instead of making external network requests.

#### Scenario: Allegro polling does not hang E2E verification

- **WHEN** the manual verification E2E test triggers a request matching `**/api/auth/allegro/**`
- **THEN** the test SHALL satisfy the request through its route interceptor
- **AND** the test SHALL remain deterministic without waiting for the external Allegro service
