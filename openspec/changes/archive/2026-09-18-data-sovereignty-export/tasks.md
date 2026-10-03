## 1. Core Semantic Serialization & Export Service

- [x] 1.1 Define the canonical JSON-LD `@context` dictionary binding FRBR (`http://purl.org/vocab/frbr/core#`), Schema.org (`https://schema.org/`), Dublin Core (`http://purl.org/dc/terms/`), and iqoqo (`https://iqoqo.org/ontology#`) namespaces in `app/core/export_service.py`, verifying context structure in unit tests.
- [x] 1.2 Implement `ExportService` in `app/core/export_service.py` with generator-based streaming serializers for canonical JSON-LD, RDF Turtle, and hierarchical JSON formats traversing the complete FRBR hierarchy (`Item` -> `Manifestation` -> `Expression` -> `Work`), verifying entity hierarchy and `isbn13` placement on Manifestations.
- [x] 1.3 Add batched cursor querying (`yield_per`) and relationship eager loading in `ExportService.stream_user_collection()` to support chunked streaming without loading large libraries into memory, verifying batch iteration in unit tests.

## 2. Authenticated API Endpoint

- [x] 2.1 Add `GET /api/v1/items/export` endpoint with `@require_auth` in `app/api/items.py`, validating the `format` query parameter (`json-ld`, `turtle`, `json`) and rejecting invalid formats with HTTP 400 Bad Request, verifying endpoint validation via API tests.
- [x] 2.2 Wire the streaming response with Flask `stream_with_context()`, configuring `Content-Type`, `Content-Disposition: attachment; filename=...`, and `X-Accel-Buffering: no` headers, verifying chunked transfer encoding with test client.

## 3. Frontend Profile Export Interface

- [x] 3.1 Create `frontend/lib/api/export.ts` with `downloadCollectionExport()` handling authenticated streaming fetch, extracting filenames from `Content-Disposition`, and managing download blobs and error toast notifications, verifying TypeScript types compile cleanly.
- [x] 3.2 Add the "Export Collection" card to `frontend/app/profile/page.tsx` with format selection dropdown/radios (JSON-LD, Turtle, JSON) and download action button with loading states, verifying visual rendering and interaction in profile page tests.

## 4. End-to-End Validation & Semantic Compliance

- [x] 4.1 Implement automated backend test suite in `tests/test_data_export.py` covering unauthenticated rejection, format negotiation, streaming responses, and FRBR hierarchy completeness, verifying tests pass with `pytest`.
- [x] 4.2 Validate generated JSON-LD and Turtle export outputs against the canonical ontology and SHACL shapes in `docs/ontology/iqoqo-shapes.ttl`, verifying conformity in test execution.
