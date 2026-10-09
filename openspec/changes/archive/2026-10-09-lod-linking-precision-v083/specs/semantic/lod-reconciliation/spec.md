## MODIFIED Requirements

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
