## ADDED Requirements

### Requirement: Google OAuth External API Configuration
The frontend Admin API Settings UI SHALL provide configuration fields for Google OAuth client credentials (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`) within the Google Services group on `/admin/settings?tab=apikeys`, supporting value masking, toggle-reveal, and persistence to `InstanceSettings`.

#### Scenario: Admin views Google OAuth configuration fields
- **WHEN** an admin navigates to `/admin/settings?tab=apikeys`
- **THEN** the Google Services section displays input fields for `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` with appropriate labels, placeholders, and source badges.

#### Scenario: Admin updates and saves Google OAuth credentials
- **WHEN** an admin enters a new Google OAuth Client ID or Client Secret and clicks Save
- **THEN** the credentials are submitted to `PUT /api/admin/settings`, persisted encrypted into `InstanceSettings`, and reflected on subsequent loads.
