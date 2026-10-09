# semantic/lod-reconciliation Specification

## Purpose

Provides batch Linked Open Data (LOD) reconciliation controls for administrators and custodians, asynchronous progress tracking with per-authority metrics (DBpedia, GeoNames, WordNet), real-time audit resolution logs, and end-to-end verification.

## Requirements

### Requirement: Batch LOD Reconciliation Trigger

The system SHALL allow authorized administrators and catalog custodians (users with `admin` or `custodian` role, or granted `refetch:metadata` permission) to initiate catalog-wide or filtered batch LOD entity reconciliation jobs asynchronously.

#### Scenario: Triggering catalog-wide reconciliation

- **WHEN** an administrator or custodian submits a request to reconcile the entire catalog
- **THEN** the system enqueues a background reconciliation job, returns HTTP 202 Accepted with a unique task ID, and begins chunked processing across all manifestations.

#### Scenario: Scoping reconciliation to unlinked items only

- **WHEN** an administrator or custodian selects the "unlinked only" filter and submits a reconciliation request
- **THEN** the system filters target manifestations to those without existing semantic links and schedules reconciliation exclusively for those entities.

#### Scenario: Rejecting duplicate concurrent reconciliation requests

- **WHEN** an administrator or custodian requests batch reconciliation while another reconciliation task is actively running
- **THEN** the system rejects the request with HTTP 409 Conflict, returning the ID of the active task without scheduling redundant background work.

#### Scenario: Defaulting scan options to unlinked items

- **WHEN** an administrator or custodian opens the scan options dropdown
- **THEN** the "unlinked only" filter is enabled by default to prevent redundant re-querying of already enriched items.

#### Scenario: Rejecting unauthorized reconciliation requests

- **WHEN** an unauthenticated user or an ordinary collector without admin, custodian, or metadata curation permissions requests batch reconciliation
- **THEN** the system denies the request with HTTP 401 Unauthorized or HTTP 403 Forbidden without scheduling any background tasks.

### Requirement: Asynchronous Progress and Authority Metric Tracking

The system SHALL track batch reconciliation progress in real time, computing counts of links resolved per external authority (DBpedia, GeoNames, WordNet) alongside total items processed, and maintain an active task registry to support client rehydration.

#### Scenario: Querying active task status

- **WHEN** a client queries `GET /api/admin/lod/tasks/active`
- **THEN** the system checks the Redis active task key and returns the in-flight task ID and progress payload, or `null` if no reconciliation job is currently executing.

#### Scenario: Streaming live progress and per-authority counts

- **WHEN** a client polls or listens to the progress of an active reconciliation task
- **THEN** the system returns the total items count, items processed count, percentage completion, and a breakdown of new links attributed to DBpedia, GeoNames, and WordNet.

#### Scenario: Calculating linked editions across entity hierarchy

- **WHEN** an administrator or custodian requests catalog LOD lifetime statistics
- **THEN** the system counts distinct manifestations that either possess direct semantic links or whose parent Work possesses semantic links, correctly reflecting the total enriched editions.

#### Scenario: Monitoring completed batch job summary

- **WHEN** all manifestation chunks in a batch reconciliation job finish processing
- **THEN** the task state transitions to completed, clearing the active task registry key, recording final aggregate execution duration, total resolved links, and cumulative authority counts.

#### Scenario: Throttled execution and rate-limit backoff

- **WHEN** external LOD providers return rate-limit or transient error responses during batch processing
- **THEN** the background task applies exponential retry backoff and throttles requests between chunks without terminating the overall job.

### Requirement: Live Item-by-Item Resolution Audit Log Stream

The system SHALL maintain and expose a structured recent resolution audit stream recording item-level matching outcomes, authority link additions, and skips or errors.

#### Scenario: Retrieving recent resolution audit events

- **WHEN** an administrator or custodian inspects active or recent reconciliation job progress
- **THEN** the system returns a chronological log buffer containing timestamp, manifestation ID, title, status (success, skipped, failed), and matched external URIs.

#### Scenario: Recording zero-match or skipped entities

- **WHEN** an item metadata query yields no candidate links above the confidence threshold
- **THEN** the system logs an informational skip event noting that zero links were added, allowing the batch process to continue uninterrupted.

### Requirement: Administrative & Custodian Reconciliation Dashboard UI

The system SHALL provide a reconciliation user interface accessible to administrators and custodians displaying real-time reconciliation metrics, single primary action trigger, suggested link counts, false-positive cleanup trigger, and a filterable audit log stream adhering to UX button density heuristics.

#### Scenario: Reconnecting to active batch task on page reload

- **WHEN** an administrator or custodian reloads `/admin/lod` while a batch reconciliation task is running
- **THEN** the interface checks the active task endpoint, restores the active task ID, displays the running progress bar, disables the start scan button, and resumes streaming the live audit log.

#### Scenario: Viewing real-time authority breakdown cards and drill-down

- **WHEN** an administrator or custodian visits `/admin/lod`
- **THEN** the interface renders summary metric cards displaying total processed manifestations, accepted links attributed to DBpedia, GeoNames, and WordNet, and suggested links awaiting curation, where each card functions as a clickable navigation link to `/collection` or the review queue.

#### Scenario: Executing reconciliation with live progress feedback

- **WHEN** an administrator or custodian clicks the primary "Start Full Scan" button
- **THEN** the button transitions to a loading state, a progress bar appears displaying percentage completion, and the live log stream populates in real time.

#### Scenario: Refreshing lifetime statistics with explicit feedback

- **WHEN** an administrator or custodian clicks the "Refresh stats" button
- **THEN** the button displays a spinning loading indicator while fetching, disables repeat clicks, and presents a confirmation toast upon successful data refresh.

#### Scenario: Toggling auto-scroll with clear visual contrast

- **WHEN** an administrator or custodian toggles the auto-scroll button in the audit log viewer
- **THEN** the button displays high-contrast visual styling indicating clearly whether auto-scroll is active or inactive.

#### Scenario: Navigating between custodian views and LOD dashboard

- **WHEN** a custodian visits `/admin/content` or `/admin/sparql`
- **THEN** the navigation bar or header provides direct navigation tabs/links to `/admin/lod`.

#### Scenario: Filtering audit logs by authority or outcome

- **WHEN** an administrator or custodian toggles the log filter (e.g. "DBpedia", "GeoNames", "WordNet", or "Errors")
- **THEN** the displayed log stream updates immediately to display only matching resolution events.

#### Scenario: Triggering dry-run cleanup of low-confidence links

- **WHEN** an administrator or custodian executes the cleanup dry-run action from `/admin/lod`
- **THEN** the system re-scores existing links, reports the count of candidate demotions and deletions in the audit stream, and does not mutate link status until explicitly confirmed.

#### Scenario: Restricting access for non-curator users

- **WHEN** a standard collector without admin or custodian privileges navigates to `/admin/lod`
- **THEN** the user interface denies access and redirects to an unauthorized notice or dashboard view.

### Requirement: Catalog & Collection Filtering by LOD Authority

The system SHALL support filtering catalog manifestations by accepted LOD linkage status and authority in API queries and collection view facets, ignoring suggested or rejected links.

#### Scenario: Filtering collection by LOD authority

- **WHEN** a client requests manifestations with query parameter `lod_authority=dbpedia`
- **THEN** the system returns only manifestations that have accepted DBpedia links attached to themselves or their parent work.

#### Scenario: Filtering collection by linked status

- **WHEN** a client requests manifestations with query parameter `lod_status=linked` (or `lod_status=unlinked`)
- **THEN** the system returns only manifestations that have (or lack) external accepted LOD links across supported authorities.

### Requirement: Instance Settings Configuration for GeoNames

The system SHALL allow administrators to configure the GeoNames web service username dynamically in the instance settings panel, saving to `InstanceSettings` and falling back to environment configuration.

#### Scenario: Updating GeoNames username in instance settings

- **WHEN** an administrator enters a GeoNames username in the instance settings panel and saves
- **THEN** the system persists `GEONAMES_USERNAME` to `InstanceSettings`, making it immediately active for subsequent entity reconciliation queries.

#### Scenario: Falling back to environment variable when unconfigured in database

- **WHEN** `GEONAMES_USERNAME` is not defined in `InstanceSettings`
- **THEN** the reconciliation service resolves locations using `os.environ.get("GEONAMES_USERNAME")` (or fallback default).

### Requirement: Automated Multi-tier Testing and End-to-End Verification

The system SHALL validate the entire reconciliation lifecycle across backend unit tests, frontend component tests, and end-to-end browser workflows using Playwright for both Administrator and Custodian user personas.

#### Scenario: End-to-end admin and custodian workflow execution via Playwright

- **WHEN** the Playwright test suite executes the LOD reconciliation spec
- **THEN** it validates that both Administrator and Custodian accounts can successfully log in, navigate to `/admin/lod`, trigger reconciliation, observe progress bar advancement, verify metric card updates, and inspect log entries.

#### Scenario: Backend task failure and retry resilience

- **WHEN** backend unit tests simulate network timeouts during batch execution
- **THEN** tests assert that Celery task retry policies trigger as expected and partial results are preserved without transaction corruption.
