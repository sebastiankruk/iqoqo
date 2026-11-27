# v120-pre-merge-review-remediation Specification

## Purpose
Enforces pre-merge security, SQL dialect safety, mobile multi-server credential isolation, UI state sync, backfill ordering, and release-documentation hygiene before merging `release/1.2.0`.

## Requirements

### Requirement: Guarded `total_reading_minutes` Aggregation and Write Protection

The system SHALL safely parse `Item.meta["total_reading_minutes"]` in SQL average calculations without throwing database type-cast errors on non-integer strings, and SHALL prevent direct client item-update payloads from overwriting derived `total_reading_minutes` totals.

#### Scenario: PostgreSQL manifestation stats ignore non-integer `total_reading_minutes` strings

- **WHEN** a public `Item` has `meta["total_reading_minutes"]` set to a non-integer string (such as `"45.5"` or `"invalid"`)
- **THEN** `GET /api/manifestations/<id>` and `GET /api/manifestations/<id>/stats` MUST ignore the malformed value and return HTTP `200` instead of failing with HTTP `500`

#### Scenario: Direct item update cannot overwrite derived `total_reading_minutes`

- **WHEN** an authenticated item owner sends `PUT` or `PATCH /api/items/<id>` containing `total_reading_minutes` (or `reading_sessions_count` / `reading_sessions`) in extra fields or `meta`
- **THEN** `_update_physical_item()` MUST NOT persist client-supplied derived values AND MUST preserve existing session-derived `total_reading_minutes`, `reading_sessions_count`, and `reading_sessions` in `Item.meta` without erasing them

### Requirement: Multi-Media Progress Start Status Parity in Manifestation Stats

The system SHALL recognize start statuses across all supported FRBR media categories (`reading`, `currently_reading`, `listening`, `watching`, `playing`, `building`) when computing `avg_reading_days` in `_compute_manifestation_stats()`.

#### Scenario: Music, video, game, or LEGO completion produces `avg_reading_days`

- **WHEN** a public non-book `Item` records an `ItemStatusLog` transition into `listening`, `watching`, `playing`, or `building` followed by a transition into `listened`, `watched`, `played`, or `built`
- **THEN** `GET /api/manifestations/<id>/stats` SHALL include the elapsed duration in `avg_reading_days`

### Requirement: Isolated Per-Server Mobile Token Lookup and Async Active Server Resolution

Capacitor authentication storage helpers (`getAuthToken`, `setAuthToken`, `removeAuthToken`) SHALL resolve the active server profile asynchronously via `getActiveServerId()`, SHALL isolate credentials strictly per `serverId`, and SHALL NOT fall back to legacy un-scoped `AUTH_TOKEN_KEY` credentials when another server profile is active or after logout.

#### Scenario: Cold start after `localStorage` eviction preserves server-scoped token access

- **WHEN** a native device has `ACTIVE_SERVER_ID_KEY` stored in Capacitor `Preferences` while `localStorage` is empty
- **THEN** `getAuthToken()` and `setAuthToken()` SHALL resolve `getActiveServerId()` asynchronously and read or write under `iqoqo_auth_token_<serverId>` rather than un-scoped `AUTH_TOKEN_KEY`

#### Scenario: Switching to a server with no token does not leak legacy token

- **WHEN** an active scoped server profile has no token stored under `iqoqo_auth_token_<serverId>` while a stale un-scoped `AUTH_TOKEN_KEY` exists
- **THEN** `getAuthToken()` SHALL return `null` instead of sending the legacy token to the newly selected server

#### Scenario: Logging out removes both scoped and stale legacy tokens

- **WHEN** `removeAuthToken()` runs while a server profile is active
- **THEN** the system SHALL delete `iqoqo_auth_token_<serverId>` and clear any un-scoped `AUTH_TOKEN_KEY` when no conflicting legacy fallback could resurface

### Requirement: External Location Synchronization in `TaxonomyEditor`

`TaxonomyEditor` SHALL keep its physical location input synchronized whenever the `item.physical_location` prop changes externally.

#### Scenario: Editing physical location in `EditItemDialog` updates `TaxonomyEditor`

- **WHEN** `TaxonomyEditor` re-renders with an updated `item.physical_location` value (such as after saving inside `EditItemDialog`)
- **THEN** its input field MUST display the updated `item.physical_location` value without retaining stale pre-edit text

### Requirement: Lightbox `Escape` Dismissal and Backfill Safe Ordering

`ManifestationCoversGallery` SHALL dismiss its preview lightbox when the user presses `Escape`, and `scripts/migrate_author_lod_to_contributors.py` SHALL delete losing duplicate rows and flush before re-pointing surviving links without exposing unused CLI flags.

#### Scenario: Pressing `Escape` closes the contributed cover lightbox

- **WHEN** the fullscreen preview lightbox in `ManifestationCoversGallery` is open and the user presses `Escape`
- **THEN** the lightbox SHALL close cleanly

#### Scenario: Backfill deletes loser before updating winner without dead `--yes` flag

- **WHEN** `migrate_author_lod_links()` merges a conflicting `SemanticLink` into a target `Contributor`
- **THEN** it SHALL call `session.delete(loser)` and `session.flush()` prior to mutating `winner.entity_type` / `winner.entity_id`, and `scripts/migrate_author_lod_to_contributors.py` SHALL NOT expose an unimplemented `--yes` option

### Requirement: `v1.2.0` Release Spec and Changelog Finalization

Before merging `release/1.2.0`, completed `v1.2.0` OpenSpec changes (`C154`–`C158`, `C163`–`C164`, `C167`, `C169`, `C171`) SHALL be synced to `openspec/specs/` and archived, while `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`, Task `3.2` waiting on human SVGs) and deferred `v1.3.0` (`C170`) specs remain active and `docs/CHANGELOG.md` carries the concrete release date.

#### Scenario: Release branch ready for merge

- **WHEN** all implementation and test tasks in `C171` complete
- **THEN** the 9 completed `v1.2.0` OpenSpec changes plus `C171` SHALL be synced and archived cleanly, `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`) and `frbr-expression-manifestation-rdf-separation-v130` (`C170`) SHALL stay unarchived until their remaining work completes, and `docs/CHANGELOG.md` SHALL replace `## [1.2.0] - TBD` with `## [1.2.0] - 2026-11-27`
