# OpenSpec Specification: Feedback Comment Normalization

## Purpose

This specification defines the normalized relational data model for feedback ticket comments stored in the `social.feedback_comments` table.

## Requirements

### Requirement: FeedbackComment as relational table

The system SHALL store feedback comments in a dedicated `social.feedback_comments` relational table with proper foreign keys, replacing JSONB blob storage to prevent read-modify-write race conditions under concurrent admin edits.

#### Scenario: Creating a new feedback comment

- **WHEN** an admin or user adds a comment to a feedback item
- **THEN** a new row SHALL be inserted into `social.feedback_comments` with `feedback_item_id`, `user_id`, `comment_text`, and `created_at`
- **AND** no JSONB column SHALL be read-modified-written

#### Scenario: Concurrent comment additions

- **WHEN** two admin users simultaneously add comments to the same feedback item
- **THEN** both comments SHALL be persisted as separate rows without data loss
- **AND** no race condition SHALL occur on JSONB merge

#### Scenario: Listing comments for a feedback item

- **WHEN** the API retrieves comments for a feedback item
- **THEN** all comments SHALL be returned ordered by `created_at` ascending
- **AND** each comment SHALL include the author's username and timestamp
