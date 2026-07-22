## Requirements

### Requirement: Architecture documentation covers virtual wishlist items

The ARCHITECTURE.md SHALL document the UserWorkIntent model, negative-ID virtual items, and the virtual-to-physical Item transition that occurs when a user modifies a wishlist item (e.g., by adding tags).

#### Scenario: User reads about virtual items

- **WHEN** a contributor reads the Item section of ARCHITECTURE.md
- **THEN** they SHALL find a sub-section explaining that wishlist items are represented as virtual items with negative IDs derived from UserWorkIntent, and that mutating a virtual item transitions it to a physical Item record

### Requirement: Architecture documentation covers the require_physical_item decorator

The ARCHITECTURE.md SHALL document the `@require_physical_item` decorator, its role in enforcing FRBR boundaries at the API edge, and the standardized 400 Bad Request error response format.

#### Scenario: Developer reads about API decorators

- **WHEN** a developer reads about API enforcement in ARCHITECTURE.md
- **THEN** they SHALL see documentation of the require_physical_item decorator as a declarative FRBR boundary interceptor

### Requirement: Architecture documentation covers format normalization

The ARCHITECTURE.md SHALL document the format normalization pipeline including `app/core/format_normalizer.py`, `shared/format_mappings.yaml`, unknown format placeholders (`unknown_video`, `unknown_audio`, `unknown_text`), and the `make fix-physical-kinds` CLI tool.

#### Scenario: Instance admin reads about format configuration

- **WHEN** an instance admin reads the Operations & Maintenance section
- **THEN** they SHALL find a Format Normalization sub-section explaining the external-to-canonical format mapping pipeline and CLI audit/apply workflow

### Requirement: Architecture documentation covers faceted navigation

The ARCHITECTURE.md SHALL document the faceted navigation architecture including cross-FRBR filtering via subqueries, multi-select facet behavior (AND across facets, OR within facet values), `@optional_auth` on the stats/facets endpoint, and publisher extraction from both relational and JSON metadata fields using `func.coalesce`.

#### Scenario: Developer needs to understand facet filtering

- **WHEN** a developer searches ARCHITECTURE.md for faceted navigation
- **THEN** they SHALL find documentation of the `get_faceted_stats` data flow, FRBR-level count distinctions, and cross-entity filter resolution logic

### Requirement: Architecture documentation covers custody and audit models

The ARCHITECTURE.md SHALL document the `ItemCustodyEvent` (FRBR Item tier, append-only possession tracking) and `EntityAuditLog` (Work/Expression/Manifestation tier, curation history) models, their strict ontological separation, and their CIDOC CRM compliance rationale.

#### Scenario: Developer reads about database models

- **WHEN** a developer reviews the database schema section
- **THEN** they SHALL see documentation of ItemCustodyEvent and EntityAuditLog tables with their schema, purpose, and FRBR tier alignment

### Requirement: Architecture documentation covers authentication decorators

The ARCHITECTURE.md SHALL document the `@optional_auth` decorator used on public catalog endpoints (manifestations, stats/facets) to support unauthenticated global browsing while still providing user-specific data when logged in.

#### Scenario: Developer reads about authentication patterns

- **WHEN** a developer reviews the authentication section
- **THEN** they SHALL see documentation of @optional_auth as a pattern for hybrid public/authenticated endpoints

### Requirement: Architecture documentation covers shared collection UI

The ARCHITECTURE.md SHALL document the clean shared collection UI architecture, including share token-based access, simplified navbar for unauthenticated viewers, and hidden action buttons on shared collection views.

#### Scenario: Contributor reads about social architecture

- **WHEN** a contributor reads the Social & Privacy Architecture section
- **THEN** they SHALL find documentation of the shared collection UI patterns including token-based access control and viewer-specific UI simplification

### Requirement: Architecture documentation covers APScheduler context fix

The ARCHITECTURE.md SHALL document the APScheduler application context fix where scheduled cover cleanup jobs require explicit `scheduler.app.app_context()` wrapping in `run_scheduled_cover_cleanup()` to avoid RuntimeError outside of application context.

#### Scenario: Developer reads about background jobs

- **WHEN** a developer reads the Operations & Maintenance section
- **THEN** they SHALL see documentation of the APScheduler context requirement for background cover cleanup jobs
