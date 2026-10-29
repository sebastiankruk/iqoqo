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

#### Scenario: PAT lacking read scope does not authenticate optional-auth catalog queries

- **WHEN** a request to an optional-authentication endpoint arrives with `Authorization: Bearer iqo_...` containing only `["sparql:query"]` (without `read:catalog`, `admin`, or `*`)
- **THEN** the endpoint does not authenticate the caller as the token owner or expose the owner's private or friends-only items

#### Scenario: Scoped PATs succeed on SPARQL, inventory, and curator endpoints

- **WHEN** a user authenticates with a `"sparql:query"` PAT on `POST /api/sparql`, a `"write:inventory"` PAT on item mutation routes, or a `"curator"` PAT (minted by a custodian/contributor) on custodian endpoints
- **THEN** each endpoint authorizes the request according to its matching scope while rejecting out-of-scope operations with `403 Forbidden`

#### Scenario: Query-string token parameter is rejected on SSE stream

- **WHEN** a client requests `GET /api/v1/events/stream?token=<jwt_or_pat>` without an `HttpOnly` session cookie or `Authorization: Bearer` header
- **THEN** the endpoint rejects the query-string credential with `401 Unauthorized` so bearer secrets are not accepted in access-logged URLs

## ADDED Requirements

### Requirement: Bilingual Localization for Profile PAT and TOTP Components

The `TotpSetup` (`frontend/components/profile/totp-setup.tsx`) and `PatManagement` (`frontend/components/profile/pat-management.tsx`) components SHALL use `useTranslations("Profile")` so all headings, descriptions, buttons, table headers, badges, and dialog messages render in both English (`en.json`) and Polish (`pl.json`).

#### Scenario: Polish locale user views Profile 2FA and PAT cards

- **WHEN** an authenticated user with active locale `pl` navigates to `/profile`
- **THEN** `TotpSetup` and `PatManagement` render all UI text using Polish translations from `frontend/messages/pl.json`
