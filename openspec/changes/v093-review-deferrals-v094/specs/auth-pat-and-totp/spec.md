## ADDED Requirements

### Requirement: Bilingual Localization for Profile PAT and TOTP Components

The `TotpSetup` (`frontend/components/profile/totp-setup.tsx`) and `PatManagement` (`frontend/components/profile/pat-management.tsx`) components SHALL use `useTranslations("Profile")` so all headings, descriptions, buttons, table headers, badges, and dialog messages render in both English (`en.json`) and Polish (`pl.json`).

#### Scenario: Polish locale user views Profile 2FA and PAT cards

- **WHEN** an authenticated user with active locale `pl` navigates to `/profile`
- **THEN** `TotpSetup` and `PatManagement` render all UI text using Polish translations from `frontend/messages/pl.json`
