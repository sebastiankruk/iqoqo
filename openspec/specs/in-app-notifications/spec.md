# in-app-notifications Specification

## Purpose
social.notifications database schema, REST API, navbar notification dropdown, and real-time alerts.

## Requirements

### Requirement: In-App Notification Dispatch

The system SHALL persist and display notifications when relevant social or library events occur.

#### Scenario: Unread notification badge
- **WHEN** A new follow request arrives for a user
- **THEN** A notification record is created and the unread count in navbar increments.
