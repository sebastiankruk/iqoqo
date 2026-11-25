## MODIFIED Requirements

### Requirement: Requests Accordion Panel on Manifestation and Item Pages

The system SHALL render a collapsible "Requests" section on manifestation detail and item detail pages. This section SHALL use the Shadcn UI collapsible accordion pattern with `ChevronUp`/`ChevronDown` toggle. On manifestation detail pages, admin actions (Refetch Cover, Regenerate Cover, Edit Cover Art, Delete manifestation) MAY remain direct inline `<Button>` elements or collapsible sections. On item detail pages (`/item/[id]`), `"Admin Actions"` SHALL be rendered as a **labeled** Shadcn `DropdownMenu` trigger (`"Admin Actions"`, never an unlabeled `[...]` icon button) exposing only the actions permitted to the current user (`Refetch Metadata`, `Edit FRBR`, `Refetch Cover`, `Regenerate Cover`, `Edit Cover Art`, `Remove from library`, and `Replace Cover` / `Contribute Cover` if hosted there as the page's single canonical cover trigger), with destructive or overwrite `AlertDialog` confirmations mounted outside `DropdownMenuContent`. The `"Requests"` section SHALL contain the "Ask custodians for help" submission trigger and the list of the current user's escalation requests for that target entity.

#### Scenario: Non-custodian user opens the Requests accordion

- **WHEN** an authenticated user without `write:metadata` permission clicks the "Requests" accordion header on a manifestation detail page
- **THEN** the system SHALL expand the panel to reveal the "Ask custodians for help" button and a list of the user's previously submitted escalation requests for this target.

#### Scenario: Non-custodian user has no existing requests for this target

- **WHEN** an authenticated user without `write:metadata` permission expands the "Requests" accordion on a manifestation they have never submitted a request for
- **THEN** the system SHALL show only the "Ask custodians for help" button and no request cards.

#### Scenario: Custodian views the manifestation page

- **WHEN** an authenticated user with `write:metadata` permission views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion (since the custodian sees "Edit FRBR" instead and has no need for help requests).

#### Scenario: Unauthenticated user views the manifestation page

- **WHEN** an unauthenticated user views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion.

#### Scenario: Owner or admin opens labeled Admin Actions dropdown on item detail page

- **GIVEN** an authenticated owner or administrator with permitted administrative actions viewing `/item/[id]`
- **WHEN** the user activates the labeled `"Admin Actions"` `DropdownMenu` trigger
- **THEN** a menu opens listing only the administrative actions allowed by the user's permissions and item ownership/manifestation guards
- **AND** selecting a destructive action such as `"Remove from library"` closes the menu cleanly and opens its confirmation `AlertDialog` without focus-trap deadlock

#### Scenario: Non-owner standard user does not see Admin Actions dropdown on item detail page

- **GIVEN** an authenticated non-owner user holding only standard `"user"` permissions viewing another user's public `/item/[id]`
- **WHEN** `/item/[id]` renders
- **THEN** the `"Admin Actions"` dropdown trigger is NOT rendered
- **AND** the `"Requests"` accordion or `"Ask custodians for help"` trigger remains available
