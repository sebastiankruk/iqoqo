## Purpose
Multi-agent review sweep across 0.9.x, documentation completion, and verification of mobile app discovery/auth contract.

## ADDED Requirements

### Requirement: Mobile Client Discovery & Auth Contract

The API SHALL support dynamic server discovery and PAT/JWT session bootstrap workflows required by mobile apps.

#### Scenario: Mobile client discovers server capabilities
- **WHEN** A mobile client queries /.well-known/nodeinfo and /api/auth/providers
- **THEN** Returns supported auth strategies, software version, and CORS headers.

