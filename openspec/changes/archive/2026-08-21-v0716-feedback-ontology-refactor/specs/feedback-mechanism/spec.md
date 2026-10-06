## MODIFIED Requirements

### Requirement: Feedback items table resides in social schema
The `feedback_items` table SHALL reside in the `social` database schema, not the `inventory` schema, because feedback tickets are platform admin constructs and not inventory assets.

#### Scenario: Querying feedback items after schema migration

- **WHEN** the application queries `FeedbackItem` records via SQLAlchemy ORM
- **THEN** the query SHALL target the `social.feedback_items` table
- **AND** all existing feedback data SHALL be preserved after the schema migration

#### Scenario: New feedback item creation after schema migration

- **WHEN** a user creates a new feedback item
- **THEN** the record SHALL be inserted into `social.feedback_items`
