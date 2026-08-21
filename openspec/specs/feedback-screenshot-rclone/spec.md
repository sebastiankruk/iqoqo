# OpenSpec Specification: Feedback Screenshot Rclone Storage

## Purpose

This specification defines remote cloud backup storage and retrieval for feedback ticket screenshot attachments via `rclone`.

## Requirements

### Requirement: Feedback screenshots stored via rclone

The system SHALL upload feedback screenshots to a configurable rclone remote target instead of saving them to container-local `./app/static/gallery/`, ensuring persistence across container restarts and horizontal scaling.

#### Scenario: Uploading a feedback screenshot

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** `RCLONE_FEEDBACK_REMOTE` environment variable is configured
- **THEN** the system SHALL upload the screenshot via `rclone copyto` in a Celery background task
- **AND** the feedback item SHALL store the remote URL/path reference

#### Scenario: Retrieving a feedback screenshot

- **WHEN** the API serves a feedback item with an attached screenshot
- **AND** the screenshot is stored in the rclone remote
- **THEN** the system SHALL return a URL that resolves to the screenshot

#### Scenario: rclone remote not configured — graceful fallback

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** `RCLONE_FEEDBACK_REMOTE` environment variable is NOT set
- **THEN** the system SHALL fall back to local storage at `./app/static/gallery/`
- **AND** the system SHALL log a warning about ephemeral storage
