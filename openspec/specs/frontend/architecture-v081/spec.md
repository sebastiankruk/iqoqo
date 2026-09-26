# frontend/architecture-v081 Specification

## Purpose

Establishes frontend architectural standards for domain-modularized API hooks, robust intent mutation handling, accessible modal dialogs, declarative polling, hydration consistency, and client telemetry privacy.

## Requirements

### Requirement: Modular Domain Hooks Architecture
The client application architecture SHALL expose frontend data querying and mutation operations divided into coherent domain modules (catalog, collection, stats, roadmap, user profile, intents, admin management, and system operations) with unified type signatures and backward-compatible module re-exports.

#### Scenario: Consuming domain-specific hooks

- **WHEN** client components import query or mutation operations
- **THEN** operations are resolved from modular domain packages while maintaining existing import paths

### Requirement: Resilient Intent Deletion Contract
The system SHALL handle Work intent removal requests gracefully without throwing unhandled client exceptions when the server responds with a successful empty or null-status payload.

#### Scenario: Removing an intent from a conceptual work

- **WHEN** a user removes an existing reading or wish status from a work and the server returns a successful response with status null
- **THEN** the client resolves the mutation successfully without throwing an error and invalidates relevant work intent caches

### Requirement: Accessible Confirmation Dialogs
The system SHALL present destructive or confirmation actions using accessible modal dialogs with standard keyboard navigation, focus management, and screen-reader semantics rather than blocking browser-native alerts or confirms.

#### Scenario: Confirming collection deletion

- **WHEN** a user triggers deletion of a collection
- **THEN** the application presents an accessible confirmation dialog with explicit confirm and cancel actions, and executes deletion only upon user confirmation

### Requirement: Admin Action Feedback and Notifications
The administrative user interface SHALL provide non-blocking visual toast notifications for all state-changing operations and asynchronous action failures rather than failing silently or logging errors solely to the console.

#### Scenario: Updating role permissions fails

- **WHEN** an administrator attempts to save role permissions and the request fails
- **THEN** an accessible error toast notification appears detailing the failure message, and no unhandled exceptions are raised

#### Scenario: Role creation succeeds

- **WHEN** an administrator creates a new role successfully
- **THEN** an accessible success toast notification appears confirming the created role

### Requirement: Tuned Cache Lifetimes and Declarative Polling
The client application SHALL retain FRBR metadata queries in cache for an extended duration before marking them stale, SHALL poll transient background tasks declaratively using query interval configurations rather than ad-hoc timers, and SHALL automatically stop polling once task completion states are reached.

#### Scenario: Navigating between entity views with fresh metadata

- **WHEN** a user navigates between manifestation views within the configured metadata cache window
- **THEN** previously fetched FRBR metadata is served immediately from cache without redundant network roundtrips

#### Scenario: Monitoring background cover processing

- **WHEN** an entity displays pending cover processing
- **THEN** the client polls the status endpoint on a declarative interval and stops polling immediately when the cover status transitions away from processing

### Requirement: Server/Client Hydration Consistency
The application settings and administration views SHALL render consistent initial HTML between server rendering and client hydration without mismatches driven by direct access to client-only browser window properties.

#### Scenario: Loading administration settings page

- **WHEN** a user loads the administration settings page directly via server request or browser navigation
- **THEN** the server-rendered markup matches the initial client-hydrated markup without React hydration errors or layout shift

### Requirement: Client-Side Security and Telemetry Privacy Controls
The client runtime SHALL enforce secure attributes on locale tracking cookies, validate external URLs against permitted hostnames before client-side redirection or navigation, and mask sensitive user inputs in client session monitoring and telemetry.

#### Scenario: Persisting user locale preference

- **WHEN** a user switches language in the interface
- **THEN** the locale cookie is updated with the Secure attribute to ensure HTTPS transmission

#### Scenario: Capturing telemetry session replay

- **WHEN** client session monitoring or error telemetry is recorded
- **THEN** user input fields are masked to protect personal data from exfiltration
