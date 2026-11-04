# admin-api Specification

## Purpose
TBD - created by archiving change admin-api-ux-grouping. Update Purpose after archive.

## Requirements

### Requirement: Service-Grouped External API Configuration
The frontend Admin API Settings UI SHALL group API configuration fields into logical service cards (Allegro, Twitch/IGDB, Google, Media Databases, AI & Cover Generation) rather than isolated single-field tiles.

#### Scenario: Admin configures external API keys

- **Given** an admin user navigates to `/admin` settings under `external_apis`
- **When** the external API tab loads
- **Then** credentials for each service are grouped together into service cards with explicit section titles, reveal/hide eye toggles, source badges (`DB`/`ENV`), and card-level save actions.

### Requirement: Allegro Device Flow Fallback Resolution
The backend `/api/auth/allegro/device-flow` and `/api/auth/allegro/device-token` endpoints SHALL resolve masked or omitted `client_id` and `client_secret` parameters using stored database settings or environment variables.

#### Scenario: Admin triggers Allegro Device Authorization with stored DB keys

- **Given** Allegro client credentials are already saved in the database or environment
- **When** the admin clicks "Authorize Allegro Account" in the unified Allegro service card
- **Then** the backend uses the stored credentials to initiate the device flow, returning a verification URI and user code for authorization.

### Requirement: Twitch / IGDB Credential Support
The admin settings UI and backend configuration API SHALL support `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` settings for IGDB video game metadata lookups.

#### Scenario: Admin saves Twitch API credentials

- **Given** an admin enters a Twitch Client ID and Secret in the Twitch / IGDB service card
- **When** the admin saves the settings
- **Then** the backend persists `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` into `InstanceSettings` and uses them to fetch access tokens from Twitch OAuth for IGDB queries.

### Requirement: Google OAuth External API Configuration
The frontend Admin API Settings UI SHALL provide configuration fields for Google OAuth client credentials (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`) within the Google Services group on `/admin/settings?tab=apikeys`, supporting value masking, toggle-reveal, and persistence to `InstanceSettings`.

#### Scenario: Admin views Google OAuth configuration fields
- **WHEN** an admin navigates to `/admin/settings?tab=apikeys`
- **THEN** the Google Services section displays input fields for `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` with appropriate labels, placeholders, and source badges.

#### Scenario: Admin updates and saves Google OAuth credentials
- **WHEN** an admin enters a new Google OAuth Client ID or Client Secret and clicks Save
- **THEN** the credentials are submitted to `PUT /api/admin/settings`, persisted encrypted into `InstanceSettings`, and reflected on subsequent loads.
