# wishlist/api-separation Specification

## Purpose

Provides a clean separation of virtual wishlist entries from concrete physical inventory items, establishing dedicated CRUD API endpoints, removing negative-identifier synthetic items, enabling precise FRBR Expression and Manifestation binding (supporting F15 Complex Works and F16 Container Works), and isolating wishlist views from physical inventory in the user interface.

## Requirements

### Requirement: Dedicated Wishlist CRUD Endpoint
The system SHALL provide a dedicated `/api/wishlist` REST endpoint that allows authenticated users to create, read, update, and delete wishlist entries (`UserWorkIntent`) using standard positive integer identifiers.

#### Scenario: Listing authenticated user wishlist entries

- **WHEN** an authenticated user requests `GET /api/wishlist`
- **THEN** the system SHALL return a paginated list of the user's wishlist entries with positive integer identifiers, associated Work metadata, and any bound Expression or Manifestation details

#### Scenario: Adding a Work to the wishlist

- **WHEN** an authenticated user submits `POST /api/wishlist` with a valid `work_id` and progress `status`
- **THEN** the system SHALL create and return the new wishlist entry with a unique positive identifier and default visibility

#### Scenario: Updating wishlist entry status

- **WHEN** an authenticated user sends `PUT /api/wishlist/{id}` or `PATCH /api/wishlist/{id}` with an updated progress status
- **THEN** the system SHALL persist the updated status and return the modified wishlist record

#### Scenario: Removing an entry from the wishlist

- **WHEN** an authenticated user submits `DELETE /api/wishlist/{id}` for an entry they own
- **THEN** the system SHALL remove the wishlist record and return a success confirmation

### Requirement: Strict Boundary Between Physical Inventory and Virtual Wishlist
The system inventory endpoints (`/api/items`) SHALL exclusively manage physical exemplars (`Item`, F4) and SHALL NOT synthesize, return, or accept negative-identifier virtual items.

#### Scenario: Querying inventory items excludes wishlist entries

- **WHEN** a client queries `GET /api/items` with any combination of filters
- **THEN** the system SHALL return only physical items owned by users and SHALL NOT inject synthetic negative-ID wishlist items

#### Scenario: Rejecting negative item identifiers

- **WHEN** a client sends a request to `/api/items/{id}` with a negative identifier
- **THEN** the system SHALL reject the request with an HTTP 404 Not Found or HTTP 422 Unprocessable Entity error

### Requirement: Granular FRBR Expression and Manifestation Binding
The system SHALL allow wishlist entries to target a specific Expression (F2) or Manifestation (F3) in addition to the root Conceptual Work (F1), supporting desires for specific editions, translations, F15 Complex Work parts, or F16 Container Works, and SHALL enforce FRBR hierarchy consistency.

#### Scenario: Adding a specific Manifestation edition to the wishlist

- **WHEN** a user adds a wishlist entry specifying a `manifestation_id`
- **THEN** the system SHALL bind the entry to the target Manifestation and its parent Expression and Work

#### Scenario: Adding a specific Expression translation or medium to the wishlist

- **WHEN** a user adds a wishlist entry specifying an `expression_id` without a `manifestation_id`
- **THEN** the system SHALL bind the entry to that specific Expression and its parent Work

#### Scenario: Rejecting inconsistent FRBR hierarchy binding

- **WHEN** a user attempts to create a wishlist entry where the provided `expression_id` or `manifestation_id` does not belong to the provided `work_id`
- **THEN** the system SHALL reject the request with a validation error and prevent persistence

### Requirement: Independent Frontend Wishlist Views and State Management
The system user interface SHALL provide dedicated views and state hooks for wishlist items that operate independently from physical shelf inventory views, using positive identifiers and dedicated wishlist actions.

#### Scenario: Viewing wishlist items in the interface

- **WHEN** a user navigates to the wishlist interface
- **THEN** the UI SHALL fetch records from the dedicated wishlist endpoint and display them with wishlist-specific interactions (such as edition selection and reading goal toggles) rather than physical inventory actions (such as shelf location or QR code generation)

#### Scenario: Adding an item to wishlist from catalog

- **WHEN** a user clicks "Add to Wishlist" on a catalog manifestation or work view
- **THEN** the UI SHALL dispatch the request to `/api/wishlist` and update local wishlist query cache without creating a synthetic inventory item
