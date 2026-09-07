# OpenSpec Specification: Feedback Mechanism

## Purpose

This specification defines the native user feedback and bug reporting flow, management interface, attachment rendering, and rate-limiting rules.
## Requirements
### Requirement: Submit User Feedback

The system SHALL provide a modal (accessed from the user profile dropdown) for users to submit feedback and bug reports.
Feedback items MUST support: type (Feature Request or Bug), multiple screenshot attachments, and a status lifecycle (new -> accepted -> in progress -> in validation -> closed).

#### Scenario: Submitting feedback

- **WHEN** a user opens the feedback modal, attaches screenshots, selects a type, and submits
- **THEN** the system stores the feedback locally, the modal form is completely replaced by a prominent success state, and the submit button changes to "Close".

### Requirement: Feedback Management

The system SHALL provide a dedicated full-page screen for users and admins to view and filter feedback tickets, complete with standard navigation header/footer, left-side filtering, pagination, and enhanced ticket cards (status badges, comment/attachment counts). Screenshot attachments MUST be served statically without 404 proxy errors.

#### Scenario: Viewing tickets

- **WHEN** a user or admin navigates to the feedback management screen from the "Help & Feedback" dropdown entry
- **THEN** they can view a paginated list of feedback tickets, filter them by status and type, inspect attached images, and navigate back using the standard navigation header.

### Requirement: Ticket Authorization (RBAC)

The system SHALL enforce role-based access control for viewing and managing tickets, including access to attached screenshots. Screenshots MUST be accessible to any user who has read access to the associated ticket.

#### Scenario: Admin interacting with tickets

- **WHEN** a user with the `tickets:admin` scope views a ticket
- **THEN** they can see the requester's identity, change the ticket status, leave comments, access attached screenshots, and interact with all tickets in the system.

#### Scenario: Creator interacting with tickets

- **WHEN** a user with the `tickets:creator` scope views their tickets
- **THEN** they can view the details, leave comments, close their own tickets, and access attached screenshots, but cannot alter the status arbitrarily or view others' tickets (unless explicitly permitted).

#### Scenario: Custodian interacting with tickets

- **WHEN** an assigned custodian or authorized user views a ticket they have been granted access to
- **THEN** they can view the details, interact with the ticket as permitted by their role, and access attached screenshots without facing IDOR restrictions.

#### Scenario: Unauthorized user accessing screenshots

- **WHEN** an unauthorized user attempts to access a ticket's screenshot via direct URL
- **THEN** the system denies access and returns a 403 Forbidden or 404 Not Found response.

### Requirement: Feedback Rate Limiting

The feedback API SHALL restrict the number of submissions per user to prevent spam. Additionally, all feedback read and update endpoints SHALL enforce per-user rate limits to prevent denial-of-service via rapid paginated queries or status mutations.

#### Scenario: Exceeding rate limit on submission

- **WHEN** a user submits more than 5 feedback reports in an hour
- **THEN** the API returns a 429 Too Many Requests response.

#### Scenario: Exceeding rate limit on listing

- **WHEN** a user issues more than 60 GET requests to `/api/feedback` or `/api/feedback/<id>` within one minute
- **THEN** the API returns a 429 Too Many Requests response.

#### Scenario: Exceeding rate limit on updates

- **WHEN** a user issues more than 30 PATCH requests to `/api/feedback/<id>` within one minute
- **THEN** the API returns a 429 Too Many Requests response.

### Requirement: Feedback Upload File Count Limit
The feedback submission endpoint SHALL enforce a maximum of 5 screenshot attachments per ticket to prevent storage and memory exhaustion attacks.

#### Scenario: Exceeding file upload limit

- **WHEN** a user submits a feedback ticket with more than 5 screenshot files attached
- **THEN** the API returns HTTP 400 with the message "Maximum 5 screenshots allowed per ticket" and no files are persisted.

### Requirement: Pagination Parameter Clamping
The feedback listing endpoint SHALL clamp `page` and `per_page` query parameters to positive integers, preventing negative SQL OFFSET/LIMIT errors.

#### Scenario: Negative page parameter

- **WHEN** a client sends `GET /api/feedback?page=-1`
- **THEN** the API treats `page` as 1 and returns the first page of results.

#### Scenario: Excessive per_page parameter

- **WHEN** a client sends `GET /api/feedback?per_page=500`
- **THEN** the API clamps `per_page` to 100 and returns at most 100 results.

### Requirement: Closed Ticket Comment Guard
The feedback update endpoint SHALL reject comment additions to tickets with status `closed`, preventing unbounded JSONB array growth on archived records.

#### Scenario: Commenting on a closed ticket

- **WHEN** a user or admin sends a PATCH request with a non-empty `comment` field to a ticket whose status is `closed`
- **THEN** the API returns HTTP 400 with the message "Cannot add comments to a closed ticket" and the comment is not persisted.

### Requirement: Feedback Attachment Display
Feedback screenshot thumbnails SHALL preserve the original aspect ratio of uploaded images, using `object-contain` instead of `object-cover` to prevent cropping vertical mobile screenshots.

#### Scenario: Viewing a vertically-oriented screenshot

- **WHEN** a user or admin views a feedback ticket containing a vertically-oriented (portrait) mobile screenshot
- **THEN** the full image is visible within the thumbnail container without cropping, using letterboxing if necessary.

### Requirement: Nginx Payload Alignment
The reverse proxy configuration SHALL set `client_max_body_size` to at least 50M to match the backend's per-file (10MB) × max-files (5) upload validation, preventing silent 413 rejection of legitimate feedback submissions.

#### Scenario: Uploading maximum-sized attachments

- **WHEN** a user submits a feedback ticket with 5 screenshots, each approaching 10MB
- **THEN** the Nginx proxy accepts the request and forwards it to the Flask backend for validation.

### Requirement: Feedback items table resides in social schema

The `feedback_items` table SHALL reside in the `social` database schema, not the `inventory` schema, because feedback tickets are platform admin constructs and not inventory assets.

#### Scenario: Querying feedback items after schema migration

- **WHEN** the application queries `FeedbackItem` records via SQLAlchemy ORM
- **THEN** the query SHALL target the `social.feedback_items` table
- **AND** all existing feedback data SHALL be preserved after the schema migration

#### Scenario: New feedback item creation after schema migration

- **WHEN** a user creates a new feedback item
- **THEN** the record SHALL be inserted into `social.feedback_items`

### Requirement: Feedback page mobile filters use collapsible drawer
The feedback page filter sidebar SHALL be wrapped in a collapsible bottom-sheet drawer on mobile viewports (< 768px) to prevent excessive scrolling past filter controls.

#### Scenario: Mobile viewport renders filter drawer collapsed

- **WHEN** a user opens the feedback page on a mobile viewport (width < 768px)
- **THEN** the filter controls SHALL be hidden inside a collapsed drawer/sheet
- **AND** a "Filters" button or icon SHALL be visible to expand the drawer

#### Scenario: User opens and applies filters on mobile

- **WHEN** a user taps the filter button to expand the drawer
- **AND** selects filter criteria and taps "Apply"
- **THEN** the drawer SHALL close
- **AND** the feedback list SHALL update with filtered results
- **AND** the entire interaction SHALL require fewer than 3 taps

#### Scenario: Desktop viewport renders filters inline

- **WHEN** a user opens the feedback page on a desktop viewport (width >= 768px)
- **THEN** the filter controls SHALL render inline in the sidebar (unchanged behavior)
