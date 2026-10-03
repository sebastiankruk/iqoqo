## Why

Users have no self-service mechanism to export their personal library collections in standardized, open, and machine-readable Linked Data formats, risking vendor lock-in and impeding data portability. Providing a streaming export in canonical JSON-LD, RDF Turtle, and hierarchical JSON empowers users with data sovereignty and unlocks decentralized interoperability across the Semantic Web as part of the v0.8.0 release plan (C6: Data Sovereignty Export).

## What Changes

- Add a streaming export service in `app/core/export_service.py` that queries user items and serializes the complete FRBR hierarchy (`Item` -> `Manifestation` -> `Expression` -> `Work`) into canonical JSON-LD, RDF Turtle, and JSON.
- Define a custom JSON-LD `@context` binding FRBR (`http://purl.org/vocab/frbr/core#`), Schema.org (`https://schema.org/`), Dublin Core (`http://purl.org/dc/terms/`), and iqoqo ontology namespaces (`https://iqoqo.org/ontology#`).
- Expose a user-facing authenticated endpoint `GET /api/v1/items/export` accepting query parameter `format=json-ld|turtle|json` with chunked transfer encoding (streaming generator) and attachment disposition headers.
- Update `frontend/app/profile/page.tsx` with a dedicated "Export Collection" section featuring a format selector, descriptive guidance, and a streaming download button with progress/toast feedback.
- Add TypeScript helper functions in `frontend/lib/api/export.ts` to trigger streaming file downloads with authenticated session tokens.

## Capabilities

### New Capabilities
- `semantic/data-export`: User collection export in canonical JSON-LD, RDF Turtle, and hierarchical JSON formats supporting chunked streaming and custom FRBR/Schema.org/DC ontology context mappings.

### Modified Capabilities
<!-- None: introduces a dedicated export capability alongside existing catalog and profile APIs -->

## Impact

- **API & Routing**: New authenticated endpoint `GET /api/v1/items/export` on `api_bp` in `app/api/items.py` with parameter validation and rate limiting.
- **Backend Services**: New streaming serialization service in `app/core/export_service.py` using `rdflib` and batch DB cursors/generators for memory-efficient streaming.
- **Frontend**: Updated `frontend/app/profile/page.tsx` adding the Export Collection card UI, and new API helper `frontend/lib/api/export.ts`.
- **Dependencies**: Uses existing `rdflib` (v7.*), `Flask` streaming responses, and `sonner` toasts.
