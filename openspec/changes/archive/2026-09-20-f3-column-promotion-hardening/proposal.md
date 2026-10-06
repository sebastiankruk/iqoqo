## Why

The release migration narrows `publisher` before safely handling existing values, and runtime writers can still store malformed or non-canonical ISBN and format data. This can make PostgreSQL upgrades fail and allow new records that violate the typed F3 contract.

## What Changes

- Add a preflight/data-quality phase before narrowing `publisher`, with an explicit truncation, rejection, or schema-expansion policy.
- Make upgrade and downgrade behavior reversible for every promoted metadata key or document an intentional non-reversible migration with a backup requirement.
- Centralize case-insensitive legacy-key extraction and typed validation at the ingestion/service boundary.
- Convert valid ISBN-10/hyphenated values to canonical ISBN-13 and reject invalid length/checksum values where the field is ISBN-13.
- Validate `format_type` against the shared taxonomy or a documented forward-compatible vocabulary policy.
- Add PostgreSQL migration tests with long publishers, mixed-case legacy keys, malformed identifiers, and rollback checks.

## Capabilities

### New Capabilities

### Modified Capabilities

- `frbr/physical-attributes`: Require safe, reversible promotion and canonical validation of F3 physical attributes.

## Impact

- `migrations/versions/v0_7_19_f3_column_promotion.py`, `app/core/frbr_service.py`, ingestion/API schemas, and migration/data-quality tests.
- Existing deployments with long publisher values may require operator remediation before upgrade.
