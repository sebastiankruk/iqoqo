## MODIFIED Requirements

### Requirement: Personal Access Token Authentication

The system SHALL authenticate API requests using hashed Personal Access Tokens bearing the `'iqo_'` prefix, permitting `"sparql:query"` scope on `POST /api/sparql` in `require_auth` and mapping `"write:inventory"` alongside `"write:catalog"` in `require_permission`.

#### Scenario: Valid PAT grants scoped access

- **WHEN** A request arrives with Authorization: Bearer iqo_... possessing read:catalog scope
- **THEN** The request succeeds and last_used_at is updated.

#### Scenario: PAT with sparql:query scope executes POST /api/sparql

- **WHEN** A client authenticates with a PAT containing `["sparql:query"]` and sends `POST /api/sparql`
- **THEN** `require_auth` and `require_permission` allow the request without requiring `"write:catalog"`.

#### Scenario: PAT with write:inventory scope mutates item inventory

- **WHEN** A client authenticates with a PAT containing `["write:inventory"]` and calls an item creation or update route
- **THEN** `require_auth` and `require_permission` allow the inventory mutation.

## ADDED Requirements

### Requirement: Bilingual Localization for Profile PAT and TOTP Components

The `TotpSetup` (`frontend/components/profile/totp-setup.tsx`) and `PatManagement` (`frontend/components/profile/pat-management.tsx`) components SHALL use `useTranslations("Profile")` so all headings, descriptions, buttons, table headers, badges, and dialog messages render in both English (`en.json`) and Polish (`pl.json`).

#### Scenario: Polish locale user views Profile 2FA and PAT cards

- **WHEN** an authenticated user with active locale `pl` navigates to `/profile`
- **THEN** `TotpSetup` and `PatManagement` render all UI text using Polish translations from `frontend/messages/pl.json`
