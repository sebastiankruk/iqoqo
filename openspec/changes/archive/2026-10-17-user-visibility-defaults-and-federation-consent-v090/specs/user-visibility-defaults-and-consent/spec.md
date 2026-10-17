## Purpose
User-level default item visibility settings and profile Federation Consent UI.

## ADDED Requirements

### Requirement: Default Item Visibility Scoping

The system SHALL apply the user's default item visibility setting when new items are ingested or scanned.

#### Scenario: New item inherits user default visibility
- **WHEN** A user with default_item_visibility='private' scans a barcode
- **THEN** The created Item record has is_public=False.

### Requirement: Federation Opt-In Consent

The system SHALL require explicit user consent before exposing actor profile or collection data via federation.

#### Scenario: Non-consented user returns 404 on WebFinger
- **WHEN** A WebFinger query targets a user with federated_profile=False
- **THEN** The endpoint returns 404 Not Found.

