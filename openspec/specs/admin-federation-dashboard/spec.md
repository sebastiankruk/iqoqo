# admin-federation-dashboard Specification

## Purpose
Admin Federation management UI, instance trust settings, activity logs, and full i18n localization.

## Requirements

### Requirement: Admin Federation Instance Management

The admin panel SHALL allow administrators to view, discover, block, and set trust levels for remote Fediverse instances.

#### Scenario: Changing instance trust level

- **WHEN** An administrator changes instance trust from pending to trusted
- **THEN** The backend updates trust_level and future activities auto-merge metadata.
