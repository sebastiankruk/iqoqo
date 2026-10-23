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
