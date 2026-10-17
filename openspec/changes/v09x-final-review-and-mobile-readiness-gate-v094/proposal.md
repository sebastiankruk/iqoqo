## Why
Final release gate for the entire v0.9.x stream: ensures zero critical/high/moderate debt remains, documentation is 100% complete, and the server contract is ready for v1.0.0 native mobile apps.
## What Changes

- Execute full multi-agent review sweep (Security, SRE, QA, Ontologist, Architecture) across all v0.9.0–v0.9.4 code.
- Verify mobile client discovery contract (`GET /.well-known/nodeinfo`, `/api/auth/providers`, CORS, PAT/JWT refresh) required for upcoming v1.0.0 Capacitor apps.
- Finalize `docs/FEDERATION.md`, `docs/API.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`, and `docs/CHANGELOG.md`.

## Capabilities

### New Capabilities
- `v09x-review-mobile-readiness`: Multi-agent review sweep across 0.9.x, documentation completion, and verification of mobile app discovery/auth contract

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Final quality gate before v1.0.0 mobile milestone.
