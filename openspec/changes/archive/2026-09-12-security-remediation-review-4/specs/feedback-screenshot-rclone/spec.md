## ADDED Requirements

### Requirement: Feedback screenshot access authorization containment
The API SHALL enforce that access to an attachment screenshot is granted only if the authenticated user has read authorization for every ticket that references that attachment filename, preventing unauthorized access via cross-ticket collision.

#### Scenario: Authorized user reads own screenshot
- **WHEN** an authenticated user requests a screenshot referenced only in tickets they own or are authorized to read
- **THEN** the API SHALL serve the screenshot file with status 200

#### Scenario: Unauthorized access blocked across ticket collision
- **WHEN** an authenticated user requests a screenshot referenced in a ticket they can read, but the same screenshot filename is also referenced in another ticket they are not authorized to read
- **THEN** the API SHALL deny access with status 403 Forbidden
