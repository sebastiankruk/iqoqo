# container-hardening Specification

## Purpose

TBD - created by archiving change devops-sre-backup-hardening. Update Purpose after archive.

## Requirements

### Requirement: Container Security Hardening

All production container images MUST be hardened against common vulnerabilities, specifically by running application and SPARQL execution processes as non-root users with least-privilege filesystem, capability, network, and secret access.

#### Scenario: Running the application container

- **WHEN** the production Docker container is started
- **THEN** the primary application process MUST run under a dedicated, unprivileged user account (e.g., `appuser`) rather than `root`
- **THEN** the container MUST start up successfully with all necessary file permissions granted to the unprivileged user

#### Scenario: Running the SPARQL execution service

- **WHEN** the dedicated SPARQL service is started
- **THEN** it MUST run without application secrets or database write credentials, use explicit CPU, memory, and PID limits, and expose no public listener

#### Scenario: SPARQL service filesystem and network access

- **WHEN** the SPARQL service executes a query
- **THEN** its filesystem MUST be read-only except for an explicitly bounded temporary area and its network access MUST be restricted to required internal dependencies
