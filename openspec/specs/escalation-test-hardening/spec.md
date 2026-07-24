## ADDED Requirements

### Requirement: Backend escalation queue filters by status parameter
The `GET /api/escalations/queue` endpoint SHALL accept an optional `?status=` query parameter containing comma-separated status values. When absent, the endpoint SHALL default to `pending`. Valid status values are `pending`, `accepted`, `rejected`, `duplicate`. Invalid status values SHALL return a 400 response with the list of allowed statuses sorted alphabetically.

#### Scenario: Queue returns only pending by default
- **WHEN** a custodian calls `GET /api/escalations/queue` without a `status` parameter
- **THEN** the response SHALL contain only escalations with `status: "pending"`

#### Scenario: Queue returns resolved escalations when filter is applied
- **WHEN** a custodian calls `GET /api/escalations/queue?status=accepted,rejected,duplicate`
- **THEN** the response SHALL contain only escalations with status `accepted`, `rejected`, or `duplicate`

#### Scenario: Queue returns specific single status
- **WHEN** a custodian calls `GET /api/escalations/queue?status=rejected`
- **THEN** the response SHALL contain only escalations with `status: "rejected"`

#### Scenario: Invalid status parameter returns 400
- **WHEN** a custodian calls `GET /api/escalations/queue?status=imaginary`
- **THEN** the response SHALL return HTTP 400 with an error message containing the sorted list of allowed statuses

#### Scenario: Mixed valid-and-invalid statuses returns 400
- **WHEN** a custodian calls `GET /api/escalations/queue?status=pending,bogus`
- **THEN** the response SHALL return HTTP 400 with an error message

### Requirement: Backend escalation resolution tests all status variants
The `PATCH /api/escalations/<id>/resolve` endpoint SHALL accept `rejected` and `duplicate` resolution statuses in addition to `accepted`. Each resolution SHALL set `resolved_at` to the current UTC timestamp. Rejecting or marking duplicate SHALL require the `escalate:resolve` permission.

#### Scenario: Custodian rejects a pending escalation
- **WHEN** a custodian calls `PATCH /api/escalations/<id>/resolve` with `{"status": "rejected"}`
- **THEN** the escalation status SHALL be `rejected` and `resolved_at` SHALL not be null

#### Scenario: Custodian marks a pending escalation as duplicate
- **WHEN** a custodian calls `PATCH /api/escalations/<id>/resolve` with `{"status": "duplicate"}`
- **THEN** the escalation status SHALL be `duplicate` and `resolved_at` SHALL not be null

### Requirement: Resolver display name is present in queue API responses
The `GET /api/escalations/queue` endpoint SHALL include the `resolver_display_name` field in each escalation object. For resolved escalations, this SHALL be the resolver user's display name. For pending escalations, it SHALL be null. The endpoint SHALL use eager loading to fetch the resolver relationship and avoid N+1 queries.

#### Scenario: Resolved escalation includes resolver display name
- **WHEN** a custodian calls `GET /api/escalations/queue?status=accepted` after resolving an escalation
- **THEN** the resolved escalation object SHALL contain `resolver_display_name` equal to the resolving custodian's display name

#### Scenario: Pending escalation has null resolver display name
- **WHEN** a custodian calls `GET /api/escalations/queue` with default status
- **THEN** each pending escalation object SHALL have `resolver_display_name: null`

### Requirement: Escalation targets work, expression, and item levels
The `POST /api/escalations` endpoint SHALL accept `target_type` values of `work`, `expression`, `manifestation`, and `item`. The `target_id` SHALL reference an existing entity of the specified type. Non-existent targets SHALL return 404.

#### Scenario: Create escalation targeting a work
- **WHEN** a user submits an escalation with `target_type: "work"` and a valid `target_id`
- **THEN** the escalation SHALL be created with status `pending` and SHALL reference the work entity

#### Scenario: Create escalation targeting an expression
- **WHEN** a user submits an escalation with `target_type: "expression"` and a valid `target_id`
- **THEN** the escalation SHALL be created with status `pending`

### Requirement: Deletion request UI renders correctly in escalation queue
The `EscalationQueue` component SHALL distinguish correction requests from deletion requests visually. Deletion requests SHALL display a distinct badge. The accept-and-delete button SHALL be gated on the custodian possessing the corresponding delete permission.

#### Scenario: Deletion request shows deletion badge in queue
- **WHEN** the escalation queue renders a request with `request_type: "deletion"`
- **THEN** a "Deletion" badge SHALL be visible distinct from the "Correction" badge

#### Scenario: Accept-and-delete button requires delete permission
- **WHEN** a custodian without `delete:manifestation` permission views a deletion request
- **THEN** the accept button SHALL show a permission-required tooltip and SHALL not trigger deletion

### Requirement: Processed requests section renders with toggle in escalation queue
The `EscalationQueue` component SHALL include a "Processed Requests" section below the pending queue. This section SHALL be collapsed by default with a toggle button. Expanding it SHALL fetch resolved escalations using `useResolvedEscalations()`. The section SHALL handle loading, empty, error, and data states.

#### Scenario: Processed requests section is collapsed by default
- **WHEN** the escalation queue renders
- **THEN** a "Processed Requests" toggle button SHALL be visible but the resolved requests SHALL not be rendered

#### Scenario: Toggle reveals resolved escalations
- **WHEN** the user clicks the "Processed Requests" toggle
- **THEN** the section SHALL expand, fetch resolved escalations, and display resolved request cards with resolver display name

#### Scenario: Processed requests section shows loading state
- **WHEN** the toggle is clicked and resolved data is still loading
- **THEN** a loading skeleton or spinner SHALL be displayed

#### Scenario: Processed requests section shows empty state
- **WHEN** the toggle is clicked and no resolved escalations exist
- **THEN** an empty state message SHALL be displayed

### Requirement: Navbar renders My Help Requests link with pending count badge
The Navbar component SHALL render a "My Help Requests" dropdown menu item for authenticated users. The item SHALL display a pending-count badge when the user has pending escalation requests. The badge SHALL be hidden when the count is zero. The link SHALL navigate to the profile page with `#help-requests` hash.

#### Scenario: My Help Requests link visible with pending badge
- **WHEN** an authenticated user with 3 pending escalations views the navbar
- **THEN** a "My Help Requests" link SHALL be visible with a badge showing "3"

#### Scenario: Badge hidden when no pending escalations
- **WHEN** an authenticated user with 0 pending escalations views the navbar
- **THEN** the "My Help Requests" link SHALL be visible but no badge SHALL be rendered

### Requirement: Escalation utilities provide correct target links
The `escalation-utils.tsx` module SHALL export `getTargetHref()`, `getAdminTargetHref()`, and `getTargetLabel()` functions. `getTargetHref()` SHALL return public-facing URLs (`/manifestation/{id}`, `/item/{id}`). `getAdminTargetHref()` SHALL return admin editor URLs. `getTargetLabel()` SHALL return human-readable labels with entity type and ID. When the target entity is deleted (null target_id), functions SHALL return a fallback using the preserved `target_type`.

#### Scenario: getTargetHref returns correct manifestation URL
- **WHEN** called with `target_type: "manifestation"` and `target_id: 42`
- **THEN** SHALL return `/manifestation/42`

#### Scenario: getTargetLabel returns formatted label
- **WHEN** called with `target_type: "item"` and `target_id: 100`
- **THEN** SHALL return `Item #100`

#### Scenario: getTargetHref handles deleted entity gracefully
- **WHEN** called with `target_type: "manifestation"` and `target_id: null`
- **THEN** SHALL not throw and SHALL return a fallback value

### Requirement: Escalation trigger supports multi-escalation accordion pattern
The `EscalationTrigger` component SHALL accept an optional `escalations` prop containing a pre-filtered array of escalation objects. When provided, SHALL display all existing requests inside a collapsible accordion panel. The accordion SHALL show chevron toggle for expand/collapse. The `alwaysShowDialog` prop SHALL skip the status card and always render the trigger button.

#### Scenario: Accordion shows existing escalation status card externally
- **WHEN** `EscalationTrigger` renders with `escalations=[{id:1, status:"pending"}]`
- **THEN** a "Help Request: pending" status card SHALL be visible outside the accordion

#### Scenario: Accordion expands to show request details
- **WHEN** the accordion toggle is clicked
- **THEN** the full escalation details SHALL be displayed inside the accordion

#### Scenario: alwaysShowDialog renders button without status card
- **WHEN** `EscalationTrigger` renders with `alwaysShowDialog={true}`
- **THEN** only the "Ask custodians" button SHALL be visible with no status card

### Requirement: E2E escalation workflow validates submit-to-resolve pipeline
An E2E test SHALL validate the full escalation lifecycle: a submitted escalation is visible in the admin queue, a custodian can resolve it, and the resolution is reflected in the submitter's "My Help Requests" view.

#### Scenario: End-to-end escalation workflow
- **WHEN** a custodian logs in, navigates to the "User Requests" admin tab, sees a pending request, resolves it with a note
- **THEN** the request SHALL move to the processed section and SHALL display the resolver's name and resolution note
