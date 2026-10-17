## Purpose
Two-instance E2E simulation harness, SSRF chaos testing, signature replay protection, and OpenObserve telemetry verification.

## ADDED Requirements

### Requirement: Two-Instance E2E ActivityPub Simulation

The test suite SHALL verify bidirectional WebFinger, Follow/Accept, and metadata broadcast between two simulated iqoqo instances.

#### Scenario: Full federation round-trip passes
- **WHEN** Instance A follows User on Instance B and updates metadata
- **THEN** Instance B receives, verifies, and records the event.

