## ADDED Requirements

### Requirement: Multi-Series Membership Round-Trip Synchronization

The system SHALL preserve and synchronize multi-series memberships (`series_memberships`) across all FRBR tree and item inspection endpoints and mutations. Hierarchy inspection via `GET /api/v1/admin/frbr/manifestation/{id}/tree` and physical item inspection via `GET /api/items/{id}` SHALL serialize attached `series_memberships` (including ID, series work ID, series title, and sequence). When saving Work modifications, the service layer SHALL execute database-level set reconciliation without raising query syntax exceptions when memberships are cleared, and SHALL NOT conflate membership table primary keys with series Work primary keys.

#### Scenario: Inspecting FRBR tree for a work in multiple series

- **WHEN** an authorized custodian requests `GET /api/v1/admin/frbr/manifestation/{id}/tree` for a manifestation belonging to a multi-series Work
- **THEN** the returned Work object includes the `series_memberships` array containing `series_work_id`, `sequence`, and series `title`.

#### Scenario: Clearing all series memberships from a Work

- **WHEN** an authorized user updates a Work with `series_memberships: []`
- **THEN** the system removes all existing `WorkSeriesMembership` records for that work without raising an argument or boolean filter error in SQLAlchemy.

#### Scenario: Inspecting physical item with multi-series memberships

- **WHEN** a client fetches `GET /api/items/{id}` for an item associated with a series-linked Work
- **THEN** the response includes `work.series_memberships` with series title and sequence badges.
