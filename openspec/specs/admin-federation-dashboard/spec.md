# admin-federation-dashboard Specification

## Purpose
Admin Federation management UI, instance trust settings, activity logs, and full i18n localization.

## Requirements

### Requirement: Admin Federation Instance Management

The admin panel SHALL allow administrators to view, discover, block, and set trust levels for remote Fediverse instances.

#### Scenario: Changing instance trust level

- **WHEN** An administrator changes instance trust from pending to trusted
- **THEN** The backend updates trust_level and future activities auto-merge metadata.

### Requirement: Localized and Tested Admin Federation Dashboard
The Admin Federation Dashboard (`/admin/federation`, `federation-instances.tsx`, `federation-activity.tsx`, and `instance-settings.tsx`) SHALL use `useTranslations("AdminFederation")` for all user-visible labels, provide `aria-label` attributes on icon-only controls, constrain `FEDERATION_DEFAULT_TRUST` to valid trust levels (`untrusted`, `pending`, `trusted`), and be covered by Vitest unit tests.

#### Scenario: Admin federation components render localized labels and constrained trust selector

- **WHEN** an administrator views `/admin/federation` or the Federation section of `/admin/settings` in English or Polish
- **THEN** all headings, table columns, filters, and dialogs render localized strings from `AdminFederation` and `FEDERATION_DEFAULT_TRUST` is selected via a constrained dropdown
