# release-090-test-coverage Specification

## Purpose

Establishes comprehensive regression test coverage across all four architectural testing tiers (backend, frontend, operational scripts, and end-to-end workflows) for release 0.9.0 capabilities.

## Requirements

### Requirement: Federation Inbound Payload Cap Verification

The federation inbox endpoint SHALL enforce a strict 100KB payload cap, immediately rejecting oversized requests with HTTP 413.

#### Scenario: Inbound activity exceeding 100KB is rejected with 413

- **WHEN** an inbound HTTP POST request sent to `/api/federation/inbox` contains a payload larger than 100KB
- **THEN** the server returns HTTP 413 Payload Too Large without processing the JSON body

### Requirement: Federation Outbound Lookup Authentication Verification

The outbound federation discovery lookup endpoint SHALL require active user authentication, rejecting unauthenticated callers with HTTP 401.

#### Scenario: Unauthenticated lookup request is rejected with 401

- **WHEN** an unauthenticated client sends a GET request to `/api/federation/lookup` without valid credentials
- **THEN** the server returns HTTP 401 Unauthorized

### Requirement: Alembic Migration Schema Upgrade and Downgrade Verification

All 0.9.0 Alembic migrations SHALL be verified with automated round-trip upgrade and downgrade schema assertion tests.

#### Scenario: v0_9_0_federation_schema upgrades and downgrades cleanly

- **WHEN** the `v0_9_0_federation_schema` migration upgrade is executed on a clean schema
- **THEN** federation tables and constraints are created, and downgrading cleanly removes them without orphaned objects

#### Scenario: v0_9_0_user_default_visibility upgrades and downgrades cleanly

- **WHEN** the `v0_9_0_user_default_visibility` migration upgrade is executed
- **THEN** `default_item_visibility` column and its check constraint are added, and downgrading cleanly removes them

### Requirement: Item Condition and Local Barcode UI Interaction

The `EditItemDialog` component SHALL allow users to modify both `local_barcode` and `condition`, submitting updated values to the mutation hook.

#### Scenario: User updates condition and barcode in EditItemDialog

- **WHEN** a user opens `EditItemDialog`, inputs a new local barcode, and selects a different condition
- **THEN** the save action triggers `useUpdateItem` mutation with both the updated barcode and condition

### Requirement: User Profile Privacy Defaults and Consent UI

The profile page SHALL allow users to configure `default_item_visibility` and toggle federation privacy consent.

#### Scenario: User toggles default item visibility on profile page

- **WHEN** a user selects private or public for default item visibility on the profile page
- **THEN** the profile save action sends the updated `default_item_visibility` value in the update payload

#### Scenario: Federation consent controls render and update on profile page

- **WHEN** `federation_enabled` is true in instance configuration
- **THEN** the profile page displays federation privacy toggles and updates consent upon user interaction

### Requirement: Pre-Deploy Mount and Secret Permission Verification

The operational pre-deploy mount script SHALL enforce restrictive permissions on cryptographic keys and secrets.

#### Scenario: Operational mount preparation enforces strict 0700 and 0600 modes on keys

- **WHEN** `scripts/pre_deploy_mounts.py` is executed against an instance directory
- **THEN** `data/keys` directory permissions are set strictly to 0700, and `*.pem` private keys are set to 0600

### Requirement: End-to-End Barcode Editing and Privacy Consent Verification

The end-to-end integration test suite SHALL exercise real browser flows for physical item barcode updates and federation consent management.

#### Scenario: Full user workflow for physical item barcode and condition update

- **WHEN** an authenticated user opens an item detail page and submits new barcode and condition via `EditItemDialog`
- **THEN** the item detail view updates to reflect the new local barcode in the identifiers sidebar

#### Scenario: Full user workflow for federation privacy consent toggle

- **WHEN** an authenticated user visits `/profile` and toggles discoverability in the federation consent section
- **THEN** the updated consent state is saved and confirmed with a success notification
