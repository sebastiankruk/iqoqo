# in-app-notifications Specification

## Purpose
social.notifications database schema, REST API, navbar notification dropdown, and real-time alerts.

## Requirements

### Requirement: In-App Notification Dispatch

The system SHALL persist and display notifications when relevant social or library events occur.

#### Scenario: Unread notification badge

- **WHEN** A new follow request arrives for a user
- **THEN** A notification record is created and the unread count in navbar increments.

### Requirement: Notification Deep-Link Routing for Loans and Escalations
The system SHALL set `target_iri="/item/<id>"` on all loan notifications (`loan_request`, `loan_approved`, `loan_rejected`), emit `loan_approved` / `loan_rejected` notifications upon receiving inbound ActivityPub `Accept` / `Reject` responses to loan `Offer`s, and activate the Escalations tab in `FeedbackPage` when navigated to with `?tab=escalations` or `?tab=my-escalations`.

#### Scenario: Clicking an escalation_resolved notification opens the Escalations tab

- **WHEN** a user clicks an `escalation_resolved` notification linking to `/feedback?tab=my-escalations`
- **THEN** `FeedbackPage` initializes with the Curator Escalations tab active

### Requirement: Notification Rate Limiting and Complete Bilingual Localization
The `/api/v1/notifications` endpoints MUST enforce rate limiting via `@limiter.limit` consistent with other authenticated API surfaces, and all UI labels in `NotificationCenter`, `FriendsCard`, and `/feedback` (`Requests`) tabs MUST be localized via `next-intl` in both `en.json` and `pl.json` with zero hardcoded English strings.

#### Scenario: Polling notifications respects rate limits

- **WHEN** a client polls `GET /api/v1/notifications` or `POST /api/v1/notifications/read-all`
- **THEN** the backend applies explicit rate-limiter guards (`@limiter.limit`) to prevent abusive polling floods

#### Scenario: Polish locale user views NotificationCenter, FriendsCard, and Requests tabs

- **WHEN** a user with active locale `pl` opens the Notification bell popover, `/profile` Friends card, or `/feedback` (`Requests`) tabs
- **THEN** all labels, empty states, action buttons, and relative timestamps render using Polish translation keys from `frontend/messages/pl.json`

### Requirement: Actionable Friend and Follow Notification Routing
The system SHALL set `target_iri="/profile?tab=incoming#friends"` on all incoming `follow_request` and `friend_request` notifications, SHALL include the requester's identity (display name, username, and origin instance domain) in the notification payload message, and SHALL render actionable interaction controls (deep-link navigation to the incoming friends tab and direct response actions) in the Notification Center popover.

#### Scenario: Inbound follow activity generates actionable deep-linked notification

- **WHEN** an ActivityPub `Follow` activity is received for a local user
- **THEN** the system creates a `follow_request` notification with `target_iri="/profile?tab=incoming#friends"`, a payload containing the actor's username, display name, and domain, and the Notification Center renders it with an active navigation link to the incoming friends management tab.

#### Scenario: Responding directly to friend or follow request from notification center

- **WHEN** a user views a pending `friend_request` or `follow_request` in the Notification Center and clicks Accept or Reject
- **THEN** the system executes the response action via API, updates the friendship status, and marks the notification as read without requiring navigation away from the current page.
