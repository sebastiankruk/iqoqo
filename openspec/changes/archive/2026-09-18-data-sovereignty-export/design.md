## Context

See `proposal.md` for motivation and background.

iqoqo organizes personal libraries using the FRBR Group 1 ontology: `Item` (physical/digital exemplar) -> `Manifestation` (format, edition, publisher, ISBN) -> `Expression` (translation, language) -> `Work` (intellectual creation). Currently, data export is limited to an administrative full-database dump (`GET /admin/export`) implemented in `app/core/data_manager.py`, which aggregates records into an in-memory dictionary and returns a monolithic JSON file.

End-users currently have no self-service mechanism to export their personal library collections. Furthermore, the existing admin export does not produce Linked Open Data formats (JSON-LD or RDF Turtle), nor does it stream chunks, making it unsuitable for large personal collections or Semantic Web interoperability.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated user-facing authenticated endpoint `GET /api/v1/items/export` accepting `format=json-ld|turtle|json`.
- Implement `app/core/export_service.py` to stream personal library records using Python generators and Flask chunked transfer encoding (`Transfer-Encoding: chunked`).
- Enforce strict FRBR hierarchy (`Item` -> `Manifestation` -> `Expression` -> `Work`) with `isbn13` bound strictly to Manifestations (F3).
- Define a canonical JSON-LD `@context` binding `frbr:`, `schema:`, `dc:`, and `iqoqo:` namespaces.
- Add an "Export Collection" card to `frontend/app/profile/page.tsx` with format options and streaming download triggers.
- Provide client-side streaming download utility in `frontend/lib/api/export.ts` with error handling and toast notifications.

**Non-Goals:**
- Public SPARQL endpoint or arbitrary SPARQL query execution (handled in a separate semantic query change).
- Importing external JSON-LD graphs into the catalog.
- Modifying PostgreSQL database schema or adding new database migrations.
- ActivityPub actor or outbox streaming (handled in federation releases).

## Decisions

### 1. Chunked Streaming Generator Architecture
- **Decision**: Implement export serialization as a Python generator streamed directly via Flask's `Response(stream_with_context(generator), mimetype=...)`. Query user items using SQLAlchemy `yield_per(batch_size)` to stream records without loading entire collections into memory.
  - **For JSON-LD**: Stream the outer envelope (`{"@context": {...}, "@graph": [`), stream serialized entity nodes batch-by-batch, and close with `]}`.
  - **For RDF Turtle**: Stream prefix declarations upfront, then stream serialized RDF Turtle triples batch-by-batch.
  - **For Standard JSON**: Stream an array of hierarchical FRBR item objects (`[`, items, `]`).
- **Rationale**: Prevents server OOM errors and reverse proxy request timeouts for users with large collections (>10,000 items).
- **Alternatives considered**:
  - *Celery background task generating static file*: Overly complex for synchronous downloads, requires temporary file cleanup and polling endpoints.
  - *Monolithic in-memory serialization*: Memory consumption scales linearly with library size, causing worker crashes.

### 2. Canonical JSON-LD `@context` and Vocabulary Bindings
- **Decision**: Define a standardized `@context` in `app/core/export_service.py` mapping:
  - `frbr`: `http://purl.org/vocab/frbr/core#`
  - `schema`: `https://schema.org/`
  - `dc`: `http://purl.org/dc/terms/`
  - `iqoqo`: `https://iqoqo.org/ontology#`
  - Entity types: `frbr:Work`, `frbr:Expression`, `frbr:Manifestation`, `frbr:Item`.
  - Properties: `title` -> `dc:title`, `creator` -> `dc:creator`, `language` -> `dc:language`, `isbn` -> `schema:isbn`, `publisher` -> `schema:publisher`, `format` -> `schema:bookFormat`.
- **Rationale**: Retains full FRBR semantic richness while providing interoperability with Schema.org consumers and Dublin Core cataloging tools.
- **Alternatives considered**:
  - *Flat Schema.org Book*: Drops FRBR distinction between Work, Expression, Manifestation, and Item.
  - *Pure FRBR without Schema.org*: Less recognized by mainstream semantic web scrapers and search tools.

### 3. Dedicated Export Service Module
- **Decision**: Encapsulate query execution and serialization in `app/core/export_service.py` (`ExportService`), keeping `app/api/items.py` focused on routing, auth, and parameter validation.
- **Rationale**: Promotes modularity and enables comprehensive unit testing of serialization generators independently of HTTP request lifecycles.
- **Alternatives considered**: Adding export logic directly to `app/api/items.py`; rejected because `items.py` is already over 1,800 lines long.

### 4. Client-Side Download Manager
- **Decision**: Implement `exportCollection(format: string)` in `frontend/lib/api/export.ts` using `fetch()` with credentials. It initiates the download, extracts the filename from the `Content-Disposition` header, constructs a Blob/Object URL, and triggers the browser download.
- **Rationale**: Allows sending authentication tokens while handling HTTP error responses (e.g. 400 or 500) gracefully via `sonner` toasts instead of browser navigation crashes.
- **Alternatives considered**:
  - *Direct `<a href="/api/v1/items/export">` link*: Cannot display loading states or capture API error payloads to show user-friendly error messages.

## Risks / Trade-offs

- **[Risk: Monolithic graph construction causing memory spikes during Turtle serialization]** → **Mitigation**: Construct and serialize small subgraphs in batches per 100 items rather than creating a single massive `rdflib.Graph` in memory.
- **[Risk: Reverse proxy buffering breaking chunked streaming]** → **Mitigation**: Set `X-Accel-Buffering: no` response header for Nginx compatibility and ensure chunk sizes flush periodically.
- **[Risk: Client network disconnection during large export]** → **Mitigation**: Wrap streaming generators in try/finally blocks to ensure database cursor connections are released immediately upon socket disconnect.
