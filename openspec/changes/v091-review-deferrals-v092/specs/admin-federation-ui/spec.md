## MODIFIED Requirements

### Requirement: Localized and Tested Admin Federation Dashboard
The Admin Federation Dashboard (`/admin/federation`, `federation-instances.tsx`, `federation-activity.tsx`, and `instance-settings.tsx`) SHALL use `useTranslations("AdminFederation")` for all user-visible labels, provide `aria-label` attributes on icon-only controls, constrain `FEDERATION_DEFAULT_TRUST` to valid trust levels (`untrusted`, `pending`, `trusted`), and be covered by Vitest unit tests.

#### Scenario: Admin federation components render localized labels and constrained trust selector
- **WHEN** an administrator views `/admin/federation` or the Federation section of `/admin/settings` in English or Polish
- **THEN** all headings, table columns, filters, and dialogs render localized strings from `AdminFederation` and `FEDERATION_DEFAULT_TRUST` is selected via a constrained dropdown
