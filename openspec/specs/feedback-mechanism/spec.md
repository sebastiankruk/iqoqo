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

The system SHALL enforce role-based access control for viewing and managing tickets.

#### Scenario: Admin interacting with tickets

- **WHEN** a user with the `tickets:admin` scope views a ticket
- **THEN** they can see the requester's identity, change the ticket status, leave comments, and interact with all tickets in the system.

#### Scenario: Creator interacting with tickets

- **WHEN** a user with the `tickets:creator` scope views their tickets
- **THEN** they can view the details, leave comments, and close their own tickets, but cannot alter the status arbitrarily or view others' tickets (unless explicitly permitted).

### Requirement: Feedback Rate Limiting

The feedback API SHALL restrict the number of submissions per user to prevent spam.

#### Scenario: Exceeding rate limit

- **WHEN** a user submits more than 5 feedback reports in an hour
- **THEN** the API returns a 429 Too Many Requests response.
