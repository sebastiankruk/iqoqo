# cartographic-maps-and-supplements Specification

## Purpose

Support standalone cartographic maps/atlases and `iqoqo:hasMapAttachment` (`frbroo:R15_has_part`) map supplements on Books, Board Games, and Video Games with Item-level insert completeness tracking.

## Requirements

### Requirement: Standalone Cartographic Map & Entity Map Supplement Modeling

The system SHALL support cataloging standalone cartographic media (`cartographic_map`, `atlas` with `map_scale` and `map_projection`) AND attaching map supplements (`iqoqo:hasMapAttachment` / `frbroo:R15_has_part`) to Books, Board Games, and Video Games, while tracking physical insert presence (`map_insert_present`) on the `Item` (F5) tier.

#### Scenario: Attaching a fold-out or cloth map to a Book or Game Manifestation

- **GIVEN** an existing Book or Video Game `Manifestation`
- **WHEN** an authenticated contributor uploads or attaches a map supplement (`map_type="cloth_map"`, `title="Map of Skyrim"`)
- **THEN** the `Manifestation` records the map attachment, RDF serialization emits `iqoqo:hasMapAttachment`, and individual `Item` owners can toggle `map_insert_present` on their physical copy.

### Requirement: Map Attachment URL Validation, Field Bounds, and Audit Logging (`C-01`)

`POST /api/manifestations/<id>/map-attachments` and `DELETE /api/manifestations/<id>/map-attachments/<attachment_id>` MUST enforce strict URL scheme/SSRF validation, string length limits, attachment count caps, and `EntityAuditLog` tracking.

#### Scenario: Reject `javascript:` or `data:` URI in map attachment

- **GIVEN** an authenticated user who owns an Item of Manifestation `M` (or a custodian)
- **WHEN** `POST /api/manifestations/<M.id>/map-attachments` is called with `{"image_url": "javascript:alert(1)", "title": "World Map"}` or `{"image_url": "data:text/html,<script>alert(1)</script>"}`
- **THEN** the endpoint MUST reject the request with HTTP `400 Bad Request` and MUST NOT persist the attachment in `Manifestation.meta["map_attachments"]`.

#### Scenario: Enforce string length bounds, max attachment count, and EntityAuditLog

- **GIVEN** an authenticated user adding or deleting a map attachment on Manifestation `M`
- **WHEN** `title` exceeds 200 characters, `scale` or `projection` exceeds 100 characters, `image_url` exceeds 500 characters, or `Manifestation.meta["map_attachments"]` already has 20 attachments
- **THEN** the endpoint MUST return HTTP `400 Bad Request`
- **AND WHEN** a valid attachment is added or deleted, the endpoint MUST record an `EntityAuditLog` entry for `entity_type="Manifestation"` and `entity_id=M.id`.
