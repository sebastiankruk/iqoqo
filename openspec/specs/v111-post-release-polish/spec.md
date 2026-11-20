# v111-post-release-polish Specification

## Purpose
Tracks low-severity backend query hygiene, RDF/serial edge-case hardening, vision status polish, and collection bulk UX refinements deferred from the v1.1.0 code review into v1.1.1.

## Requirements

### Requirement: Shared collection endpoints avoid redundant lookups and unsafe SSR caching
The system SHALL resolve shared collection items and cache privacy (`is_private_cache`) in a single lookup pass per request, and Next.js SSR share fetching SHALL NOT cache non-public (`friends_and_public` or `all`) share payloads in the 60-second ISR Data Cache when the backend responds with `Cache-Control: private, no-store`.

#### Scenario: Private-scope share link is not retained in SSR ISR cache

- **WHEN** an anonymous visitor fetches a share link whose backend response carries `Cache-Control: private, no-store`
- **THEN** Next.js SSR does not serve stale private-scope items after the owner tightens or revokes the share token

### Requirement: Work-level reading status rollup is deterministic and ignores unmapped statuses
The system SHALL resolve equal-rank consumption statuses (such as `read` and `listened`) deterministically in `Work` reading rollups, SHALL ignore unmapped rank-0 status values (such as `"unread"` or legacy unknown strings), and SHALL execute `work_read_status` filter subqueries using SQLAlchemy 2.0 `select()`.

#### Scenario: Equal-rank completed items produce deterministic rollup status

- **WHEN** a user owns both a `read` book and a `listened` audiobook under the same `Work`
- **THEN** repeated queries always return the same deterministic `work_reading_status`

#### Scenario: Unmapped status string does not leak into `work_reading_status`

- **WHEN** a user owns an item with an unmapped or `"unread"` status string and no tracked progress status
- **THEN** `work_reading_status` evaluates to `null` rather than leaking the unmapped string

### Requirement: Serial RDF serialization, expression-scoped dedupe, weekly add-ons, and outbound telemetry are hardened
The system SHALL forward `publication_year` on dict-based collection RDF exports, SHALL guard integer conversions in serial RDF triple emission against malformed legacy strings, SHALL scope `(issue_number, publication_year)` deduplication to the parent `Expression` rather than across all expressions of the `Work`, SHALL accept weekly EAN-2 issue add-ons `01`–`53`, and SHALL emit outbound OpenTelemetry spans/metrics for serial lookup fetchers.

#### Scenario: Malformed numeric string in legacy metadata does not crash RDF export

- **WHEN** a legacy manifestation JSON contains a non-numeric `publication_year` or `cumulative_issue_number`
- **THEN** RDF serialization skips the malformed literal gracefully instead of raising `ValueError`

#### Scenario: Weekly magazine EAN-2 add-on 42 is parsed cleanly

- **WHEN** a periodical barcode or cover label carries week add-on `42`
- **THEN** the parser recognizes issue `42` without rejecting add-ons above `12`

### Requirement: Vision headline filtering, Ollama-only readiness, and collection bulk UX are polished
The system SHALL filter cover OCR headline candidates against the dynamically resolved serial title rather than a hardcoded magazine name, SHALL report `vision_ready` accurately for configured Ollama-only deployments without requiring `probe=true`, SHALL count distinct `Item.id` values for `total_physical` in `GET /api/items`, SHALL clear selected bulk item IDs on `/collection` filter/query/scope/view changes, and SHALL close the bulk-visibility dropdown on outside click or `Escape`.

#### Scenario: Changing collection filters clears hidden bulk selection

- **WHEN** a user selects items on `/collection` and then changes visibility filter, search query, scope, or view mode
- **THEN** `selectedItemIds` resets to empty so bulk actions never mutate off-screen items
