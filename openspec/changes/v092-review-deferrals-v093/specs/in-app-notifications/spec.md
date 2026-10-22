## ADDED Requirements

### Requirement: Notification Rate Limiting and Complete Bilingual Localization
The `/api/v1/notifications` endpoints MUST enforce rate limiting via `@limiter.limit` consistent with other authenticated API surfaces, and all UI labels in `NotificationCenter`, `FriendsCard`, and `/feedback` (`Requests`) tabs MUST be localized via `next-intl` in both `en.json` and `pl.json` with zero hardcoded English strings.

#### Scenario: Polling notifications respects rate limits
- **WHEN** a client polls `GET /api/v1/notifications` or `POST /api/v1/notifications/read-all`
- **THEN** the backend applies explicit rate-limiter guards (`@limiter.limit`) to prevent abusive polling floods

#### Scenario: Polish locale user views NotificationCenter, FriendsCard, and Requests tabs
- **WHEN** a user with active locale `pl` opens the Notification bell popover, `/profile` Friends card, or `/feedback` (`Requests`) tabs
- **THEN** all labels, empty states, action buttons, and relative timestamps render using Polish translation keys from `frontend/messages/pl.json`
