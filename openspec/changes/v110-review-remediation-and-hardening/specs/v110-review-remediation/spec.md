## Purpose

Enforces pre-tag security, shared-visibility correctness, bounded graph query performance, safe vision/upload handling, atomic serial ingestion, and SSR hydration safety for the iqoqo v1.1.0 release.

## ADDED Requirements

### Requirement: Shared collections include `friends_only` items when permitted by scope or Friend Bonus
The system SHALL return `friends_only` physical items (even when `is_hidden` is true) on shared collection JSON, RDF, JSON-LD, RSS, and FTS search responses whenever the share token uses `friends_and_public` or `all` scope, or when an authenticated accepted friend or owner accesses a `public_only` share link. The `is_hidden = false` guard MUST apply strictly to `public` items.

#### Scenario: Friends-only item appears in `friends_and_public` share
- **WHEN** an owner shares a collection with `visibility_scope="friends_and_public"` containing a `friends_only` item (`is_hidden=True`) and a `private` item
- **THEN** the shared collection API, RDF, and RSS endpoints return the `friends_only` item and exclude the `private` item

#### Scenario: Authenticated friend receives Friend Bonus items on `public_only` share
- **WHEN** an accepted friend requests a `public_only` shared collection link containing a `friends_only` item (`is_hidden=True`)
- **THEN** the response includes both `public` and `friends_only` items and sets `Cache-Control: private, no-store`

### Requirement: Shared collection responses vary by authentication headers on public cache paths
The system SHALL emit `Vary: Authorization, Cookie` on all shared collection responses, including anonymous `public, max-age=300` responses, so downstream proxies and CDNs do not serve cached anonymous payloads to authenticated friends or owners at the same URL.

#### Scenario: Anonymous share request emits Vary header
- **WHEN** an unauthenticated client fetches a `public_only` share link
- **THEN** the HTTP response includes `Cache-Control: public, max-age=300` and `Vary: Authorization, Cookie`

### Requirement: Bulk visibility updates avoid existence oracles and synchronize downstream indexes
The system SHALL reject `PATCH /api/items/bulk-visibility` requests containing unowned or nonexistent item IDs with a uniform error without distinguishing between missing IDs and IDs owned by another user, and SHALL dispatch ActivityPub federation and FTS synchronization when items transition between public and non-public visibility.

#### Scenario: Foreign and missing item IDs return identical error status
- **WHEN** an authenticated user submits `PATCH /api/items/bulk-visibility` with either a nonexistent item ID or an item ID owned by another user
- **THEN** the API returns the same error status code and message shape without revealing whether the ID exists

#### Scenario: Visibility flip dispatches federation and search updates
- **WHEN** an owner bulk-updates items from `public` to `private` (or `private` to `public`)
- **THEN** the system persists the new visibility and enqueues ActivityPub and search synchronization alongside transition events

### Requirement: Public search scope pins non-owned items to public visibility
The system SHALL restrict non-owned items returned under `include_public=true` in catalog search strictly to `visibility == "public"` regardless of any `visibility` filter parameter supplied by the caller.

#### Scenario: Caller filters by private visibility with `include_public=true`
- **WHEN** a user runs catalog search with `include_public=true` and `visibility=friends_only,private`
- **THEN** non-owned items with `friends_only` or `private` visibility are never returned

### Requirement: Catalog relation graph endpoint is rate-limited, batched, and URL-safe
The system SHALL enforce a rate limit on `GET /api/catalog/graph`, batch database lookups and push `Item` visibility and row limits into SQL during neighborhood traversal, and URL-encode contributor names in generated `/collection?q=...` node URLs.

#### Scenario: Contributor name with reserved URL characters is encoded
- **WHEN** `GET /api/catalog/graph` emits a contributor node named `Simon & Schuster` or `G+J RBA`
- **THEN** the node `url` encodes reserved characters (`%26`, `%2B`, etc.) so `/collection?q=...` preserves the full query

#### Scenario: Excessive graph requests are rate limited
- **WHEN** a client exceeds the configured per-minute request limit on `GET /api/catalog/graph`
- **THEN** the endpoint responds with HTTP `429`

### Requirement: Vision and cover upload pipelines enforce SSRF, decompression-bomb, and serial-gating guards
The system SHALL validate Admin-configured `OLLAMA_URL` values (`http`/`https` schemes only, stripping embedded credentials, blocking link-local/cloud metadata ranges `169.254.0.0/16` and `fe80::/10`), SHALL NOT issue network probes when `probe_ollama=false`, SHALL return HTTP `400` on `DecompressionBombError` during cover uploads without mutating global Pillow pixel limits per request, SHALL run multi-zone serial Tesseract enrichment only when serial cues are present, and SHALL align Ollama vision timeout with the frontend polling budget.

#### Scenario: Admin rejects cloud metadata `OLLAMA_URL`
- **WHEN** an admin attempts to save `OLLAMA_URL=http://169.254.169.254/latest/meta-data`
- **THEN** the API rejects the setting with HTTP `400` and does not issue an outbound request

#### Scenario: Cover upload above pixel limit returns 400
- **WHEN** a client uploads an image that triggers Pillow `DecompressionBombError`
- **THEN** `POST /api/manifestations/<id>/cover` returns HTTP `400` with a JSON error instead of HTTP `500`

#### Scenario: Plain book cover scan skips 8-pass serial Tesseract enrichment
- **WHEN** Gemini or Ollama returns valid book metadata with no serial cues (`issn`, `977`, `indeks`, `NR/Issue`, or `magazine` format)
- **THEN** the vision pipeline returns the book metadata directly without executing multi-zone serial OCR or flipping the format to `magazine`

### Requirement: Manual serial ingestion is atomic, bounded, and hydration-safe on `/scan`
The system SHALL keep manual serial `Work`/`Expression`/`Manifestation` creation in the same database transaction as physical `Item` creation (rolling back cleanly if item creation fails), SHALL validate manual serial numeric fields (`publication_month` 1–12, `publication_year` 1400–2100, `cumulative_issue_number >= 1`), and SHALL hydrate `/scan` URL query parameters after mount or via `useSearchParams()` inside `<Suspense>` without React SSR hydration warnings.

#### Scenario: Failed item creation rolls back manual serial manifestation
- **WHEN** `POST /api/items/manual` fails during `Item` creation after building a serial `Manifestation`
- **THEN** no orphaned serial `Work`, `Expression`, or `Manifestation` remains committed in the database

#### Scenario: Invalid publication month is rejected on manual serial save
- **WHEN** a client submits `publication_month=99` to `POST /api/items/manual`
- **THEN** the endpoint rejects the payload with HTTP `400`
