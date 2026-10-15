## Purpose
ActivityPub Actor/Shared Inboxes, read-only Outbox, async handlers, and Celery queue fan-out.

## ADDED Requirements

### Requirement: ActivityPub Inbound Message Handling

The system SHALL verify signatures and process ActivityPub activities asynchronously via Celery.

#### Scenario: Valid Follow activity queued
- **WHEN** A signed Follow activity arrives at the actor inbox
- **THEN** Returns 202 Accepted and queues Celery task.

