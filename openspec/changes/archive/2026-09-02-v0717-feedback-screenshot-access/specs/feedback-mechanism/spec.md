## MODIFIED Requirements

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
