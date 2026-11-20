# v103-carryovers-federation-cleanup Specification

## Purpose
Clean up the obsolete `"Federation Coming Soon"` placeholder tab on item detail pages in favor of concise federated loan/provenance badges in `DetailsTab`, and complete SQLAlchemy 2.0 `select()` query parity across `app/api/items.py`.

## Requirements

### Requirement: Remove Placeholder Federation Tab and Surface Federated Loan/Provenance Badge
The item detail tab bar (`ItemTabs`) SHALL NOT render a `"Federation Coming Soon"` placeholder tab, and `DetailsTab` SHALL display a concise federation loan or remote peer provenance badge whenever the item carries active federated custody or remote provenance metadata.

#### Scenario: Viewing an item on a federation-enabled instance

- **GIVEN** an instance with `FEDERATION_ENABLED=true`
- **WHEN** a user opens `/item/[id]`
- **THEN** the `ItemTabs` bar MUST render only active tabs (`Details`, `Reviews`, `Gallery`, and `History` when authorized) and MUST NOT render `"Federation Coming Soon"`.

#### Scenario: Viewing an item with federated loan or provenance metadata

- **GIVEN** an item that is lent to or borrowed from a federated peer, or carries remote `_provenance` origin metadata
- **WHEN** the user views the `Details` tab on `/item/[id]`
- **THEN** `DetailsTab` MUST display a localized badge summarizing the federated loan or remote peer provenance.

### Requirement: SQLAlchemy 2.0 Query Parity in Items API
All database queries inside `app/api/items.py` SHALL use SQLAlchemy 2.0 `select()` and `db.session.execute()` statements with zero legacy `Model.query` or `db.session.query()` calls while preserving existing response payloads and authorization checks.

#### Scenario: Executing item API operations after SQLAlchemy 2.0 migration

- **GIVEN** `app/api/items.py` with all legacy `.query` calls replaced by `select()`
- **WHEN** callers exercise item listing, detail retrieval, tag/collection associations, ISBN lookup, bulk creation, and status logs
- **THEN** all endpoints MUST return identical JSON structures, pagination counts, and status codes as prior releases with zero legacy `.query` usage remaining in `app/api/items.py`.
