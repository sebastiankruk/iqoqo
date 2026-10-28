## Purpose
Asynchronous PostgreSQL full-text search re-indexing via Celery and Server-Sent Events real-time transition stream.

## ADDED Requirements

### Requirement: Background FTS Vector Recomputation

The system SHALL queue and batch-update full-text search vectors asynchronously without blocking transition writes.

#### Scenario: Transition writes return immediately
- **WHEN** An item status or custody changes
- **THEN** The HTTP response returns 200 immediately, enqueuing Celery FTS re-indexing in background.

