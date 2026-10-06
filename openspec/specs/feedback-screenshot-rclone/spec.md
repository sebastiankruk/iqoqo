# OpenSpec Specification: Feedback Screenshot Rclone Storage

## Purpose

This specification defines remote cloud backup storage and retrieval for feedback
ticket screenshot attachments, and the authorisation containment that protects
them.

Updated by `devops-infrastructure-updates` to use boto3
(`S3_BUCKET_FEEDBACK` via `app/core/s3_service.py`) instead of an `rclone` remote,
so the containers no longer need a mounted credential file. The capability name
retains "rclone" for continuity with the existing requirement identifier;
`infrastructure/devops-v082` carries the current description.

## Requirements

### Requirement: Feedback screenshots stored via rclone

The system SHALL upload feedback screenshots to a remote S3-compatible bucket
instead of keeping them only in container-local `./app/static/gallery/`, ensuring
persistence across container restarts and horizontal scaling.

Configuration comes from environment variables (`S3_BUCKET_FEEDBACK`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) rather than a mounted credential
file. The upload is performed by the `upload_feedback_screenshot` Celery task via
`app/core/s3_service.py`, which does not fork a `rclone` process.

#### Scenario: Uploading a feedback screenshot

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** `S3_BUCKET_FEEDBACK` and AWS credentials are configured
- **THEN** the system SHALL upload the screenshot to that bucket in a Celery background task
- **AND** the object key SHALL be `feedback/<filename>`, where `<filename>` is a single validated path component
- **AND** a filename that is not a single safe component SHALL be rejected before any upload is attempted

#### Scenario: Retrieving a feedback screenshot

- **WHEN** the API serves a feedback item with an attached screenshot
- **AND** the screenshot is not present in the local gallery directory
- **THEN** the system SHALL read it from the feedback bucket
- **AND** it SHALL return a URL that resolves to the screenshot

#### Scenario: rclone remote not configured — graceful fallback

- **WHEN** a user attaches a screenshot to a feedback item
- **AND** no feedback bucket is configured
- **THEN** the system SHALL fall back to local storage at `./app/static/gallery/`
- **AND** the system SHALL log that remote upload was skipped
- **AND** ticket creation SHALL still succeed, because the local file was already saved

#### Scenario: Missing object and unreachable storage are distinguished

- **WHEN** reading a screenshot from the remote bucket fails
- **THEN** an absent object SHALL return 404
- **AND** a permission, network or service failure SHALL return 502
- **AND** the distinction SHALL be derived from the S3 error code rather than from a log line

### Requirement: Feedback screenshot access authorization containment

The API SHALL enforce that access to an attachment screenshot is granted only if the authenticated user has read authorization for every ticket that references that attachment filename, preventing unauthorized access via cross-ticket collision.

Unchanged in behaviour, and re-verified against the new transport: the check runs
before the local read and before the remote read, so an unauthorized caller
cannot distinguish a local screenshot from a remote one.

#### Scenario: Authorized user reads own screenshot

- **WHEN** an authenticated user requests a screenshot referenced only in tickets they own or are authorized to read
- **THEN** the API SHALL serve the screenshot file with status 200

#### Scenario: Unauthorized access blocked across ticket collision

- **WHEN** an authenticated user requests a screenshot referenced in a ticket they can read, but the same screenshot filename is also referenced in another ticket they are not authorized to read
- **THEN** the API SHALL deny access with status 403 Forbidden
- **AND** it SHALL NOT attempt either the local or the remote read
