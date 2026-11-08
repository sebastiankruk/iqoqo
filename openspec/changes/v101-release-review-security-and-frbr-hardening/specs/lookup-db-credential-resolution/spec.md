# Delta Specification: Lookup DB Credential Resolution and Status Visibility (`C108c`)

## ADDED Requirements

### Requirement: Rebrickable Credential Visibility in `/api/system/status` and `make status` (`M-05`)

`GET /api/system/status` (`app/api/system.py`) and `scripts/iqoqo-status.sh` (`make status`) MUST include `rebrickable` (`REBRICKABLE_API_KEY`) in external provider diagnostics and environment configuration counts.

#### Scenario: Report DB-configured `REBRICKABLE_API_KEY` in `/api/system/status` and `make status`

- **GIVEN** `REBRICKABLE_API_KEY` is saved in `InstanceSettings` (DB) and unset in `.env`
- **WHEN** `GET /api/system/status` or `scripts/iqoqo-status.sh` is executed
- **THEN** `services.rebrickable` MUST report `configured: true`, `source: "db"`, and `status: "configured"`, and `iqoqo-status.sh` MUST display `Rebrickable (LEGO)` under `Metadata Lookup Providers`.
