# 📡 API Reference

Complete reference for iqoqo's REST API endpoints and Semantic Web layer (`v1.2.0`).

## Authentication

Most endpoints require JWT authentication. Obtain a token via:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "your_password"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

Use the token in subsequent requests:

```http
Authorization: Bearer eyJ...
```

Signing out revokes the token server-side, not just in the browser:

```http
POST /api/auth/logout
Authorization: Bearer eyJ...
```

The browser's logout handler **forwards the token to the backend as a `Bearer`
header before clearing the cookie**. Revocation depends on that forward: the
JWT in the cookie stays cryptographically valid until it expires unless the
backend adds its `jti` to the blocklist, so clearing the cookie alone leaves any
copy of it working.

### Personal Access Tokens (PATs)

For external integrations, developer tools, and AI agents (such as Gemini Custom Gems or custom scripts), users can generate scoped **Personal Access Tokens (PATs)** on their Profile page or via the API:

```http
POST /api/auth/tokens
Authorization: Bearer <session_jwt>
Content-Type: application/json

{
  "name": "Library Sync Script",
  "scopes": ["read:catalog", "write:catalog"],
  "expires_in_days": 90
}
```

**Response:**

```json
{
  "token": "iqo_YOUR_NEW_TOKEN_STRING",
  "data": {
    "id": 12,
    "name": "Library Sync Script",
    "token_prefix": "iqo_abcd",
    "scopes": ["read:catalog", "write:catalog"],
    "created_at": "2026-10-26T12:00:00Z",
    "expires_at": "2027-01-24T12:00:00Z",
    "last_used_at": null,
    "is_active": true
  }
}
```

> [!IMPORTANT]
> The plaintext token (`iqo_...`) is returned **only once** upon creation. iqoqo stores only a SHA-256 hash of the token at rest.

Use PATs in HTTP requests exactly like session JWTs:

```http
Authorization: Bearer iqo_YOUR_NEW_TOKEN_STRING
```

#### PAT Scope Hierarchy & Constraints

| Scope | Allowed Capabilities |
| :--- | :--- |
| `read:catalog` | Read-only access to catalog, collections, works, manifestations, and items |
| `write:catalog` | Create and modify catalog items, manifestations, and works |
| `write:inventory` | Update physical item holdings, condition, notes, and local barcodes |
| `sparql:query` | Execute SPARQL queries against public and friend-scoped knowledge graph |
| `admin` | Full administrative API access (restricted to users holding the `admin` role) |
| `*` | Superuser wildcard scope (restricted to users holding the `admin` role) |

> [!WARNING]
> Personal Access Tokens are strictly rejected on session-only management endpoints (such as `/api/auth/tokens*` and `/api/auth/2fa/*`) and require an active user session token (`403 Forbidden`).

### Two-Factor Authentication (TOTP 2FA)

iqoqo supports RFC 6238 TOTP two-factor authentication (compatible with Google Authenticator, Aegis, 1Password, and Bitwarden):

- `GET /api/auth/2fa/status` — Check whether TOTP is enabled (`{"enabled": true|false}`).
- `POST /api/auth/2fa/enroll` — Begin TOTP setup; returns base32 secret, provisioning URI, 8 single-use recovery codes, and base64 PNG QR code data URI.
- `POST /api/auth/2fa/verify` — Verify the 6-digit TOTP code (`{"code": "123456"}`) and activate 2FA (`{"success": true, "enabled": true}`).
- `POST /api/auth/2fa/disable` — Disable TOTP (requires account `password` or a valid `code` / `otp_code`: `{"success": true, "enabled": false}`).

When 2FA is enabled on an account, initial authentication against `POST /api/auth/login` with email and password returns:

```json
{
  "mfa_required": true,
  "message": "Two-factor authentication required"
}
```

The client must submit a second call to `POST /api/auth/login` containing the credentials alongside the 6-digit `otp_code` (or a recovery code) to complete authentication and receive session tokens:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "your_password",
  "otp_code": "123456"
}
```

**Response:**

```json
{
  "token": "eyJ...",
  "user": {
    "id": "018f...-uuid",
    "email": "you@example.com"
  }
}
```

### Real-Time Transition Events (SSE Stream)

Asynchronous entity transitions and background full-text search indexing updates are streamed in real time via Server-Sent Events (SSE):

```http
GET /api/v1/events/stream
Authorization: Bearer <session_jwt>
Accept: text/event-stream
```

Streams emit unnamed JSON data frames and periodic heartbeat comment frames:

```text
: connected

data: {"event": "item_updated", "data": {"item_id": 42, "user_id": "018f..."}, "timestamp": "2026-10-26T12:00:00Z"}

: ping
```

Events are strictly isolated by `user_id` to prevent cross-tenant event leakage. Clients disconnect cleanly using standard EventSource lifecycles.

### OpenAPI 3.1 Specification

- **OpenAPI 3.1 Spec (JSON):** `GET /api/docs/openapi.json`
- Covers 100% of application routes, security schemes (`BearerAuth`, `PersonalAccessToken`, `DeployToken`), accurate UUID parameter and schema representations, and FRBR component schemas.

### Permission Requirements

Access is granted by **permission**, not by role. The `contributor` role holds
every `*:metadata` permission and `transfer:item`, so a curator gets the metadata and custody workflow without
being an administrator.

| Endpoint Category                       | Permission        | Auth Type    |
| --------------------------------------- | ----------------- | ------------ |
| SPARQL                                  | `read:metadata`   | Required     |
| Data Export                             | Any authenticated | Required     |
| Semantic-link relink / delete           | `write:metadata`  | Required     |
| Duplicate review — list                 | `read:metadata`   | Required     |
| Duplicate review — scan, dismiss, merge | `write:metadata`  | Required     |
| Custodian provider merge                | `write:metadata`  | Required     |
| Work series membership mutate           | `write:metadata`  | Required     |
| Work series search autocomplete         | `read:metadata`   | Required     |
| Item custody reassignment               | `transfer:item`   | Required     |
| Public Linked Data                      | None              | Not required |
| Public Feeds                            | None              | Not required |

### Admin Endpoints

Administrative and curation endpoints live on the `admin` blueprint, mounted at
`/api/v1/admin`. All state-mutating routes are audit-logged with the acting user.

| Route                                                  | Method | Permission       | Purpose                                                               |
| ------------------------------------------------------ | ------ | ---------------- | --------------------------------------------------------------------- |
| `/api/v1/admin/duplicates/`                            | `GET`  | `read:metadata`  | Paginated pending-candidate queue; filter by tier, status, confidence |
| `/api/v1/admin/duplicates/scan`                        | `POST` | `write:metadata` | Trigger a detection run                                               |
| `/api/v1/admin/duplicates/<id>/dismiss`                | `POST` | `write:metadata` | Mark a false positive                                                 |
| `/api/v1/admin/duplicates/<id>/merge`                  | `POST` | `write:metadata` | Execute a transactional merge for a chosen primary                    |
| `/api/v1/admin/frbr/manifestation/<id>/provider-merge` | `POST` | `write:metadata` | Consolidate custodian-selected provider fragments across FRBR tiers   |
| `/api/v1/admin/works/search`                           | `GET`  | `read:metadata`  | Diacritic-insensitive series work search autocomplete                 |
| `/api/v1/admin/work-links`                             | `GET`  | `read:metadata`  | List cross-media `WorkLinkCandidate` & `WorkRelation` suggestions     |
| `/api/v1/admin/work-links/scan`                        | `POST` | `write:metadata` | Enqueue cross-media Work reconciliation scan                          |
| `/api/v1/admin/work-links/<id>/accept`                 | `POST` | `write:metadata` | Atomically accept a candidate pair into a `WorkRelation`              |
| `/api/v1/admin/work-links/<id>/reject`                 | `POST` | `write:metadata` | Dismiss a cross-media Work link candidate                             |
| `/api/v1/admin/work-links/manual`                      | `POST` | `write:metadata` | Create a direct manual cross-media `WorkRelation`                     |
| `/api/v1/admin/ownership/items`                        | `GET`  | `transfer:item`  | Paginated item ownership list for custody inspection & transfer       |
| `/api/v1/admin/ownership/preview`                      | `POST` | `transfer:item`  | Preview item custody ownership transfer impact                        |
| `/api/v1/admin/ownership/reassign`                     | `POST` | `transfer:item`  | Atomically execute item custody ownership transfer                    |

A scan defaults to the `heuristic` engine, which classifies candidate pairs
without contacting an inference service:

```json
{ "tier": "all", "engine": "heuristic" }
```

`engine` accepts `heuristic` (default) or `llama`. Under `heuristic` a scan
completes with no inference service reachable; `llama` submits only the pairs the
classifier could not decide. Merge requests are rate limited.

### Test-Only Endpoints

`POST /api/lending/test/reset` resets lending state for E2E runs. It is gated on
the `TESTING` flag **and** requires a matching `X-E2E-Reset-Secret` header,
compared in constant time. When `E2E_RESET_SECRET` is unset the endpoint refuses
every request rather than falling open.

---

## SPARQL & Public Linked Data Endpoints

Full SPARQL queries, `Accept` content-negotiation headers, JSON-LD contexts, and `?format=` (`json-ld`, `turtle`, `nt`) examples live in the **[Semantic Web Guide](SEMANTIC_WEB.md)**.

### `GET /api/sparql` & `POST /api/sparql`

- **Auth & Limits:** Requires `read:metadata` permission (`10 per minute`). Read-only (`10 KB` max query, `15s` timeout, `4` concurrent, `5,000` items / `100,000` triples graph cap).
- **Inputs:** `GET ?query=<sparql>`, or `POST` with `application/sparql-query`, `application/json` (`{"query": "..."}`), or `application/x-www-form-urlencoded`.
- **Responses:** SELECT/ASK (`application/sparql-results+json`, `+xml`, `text/csv`, `text/tab-separated-values`); CONSTRUCT/DESCRIBE (`text/turtle`, `application/ld+json`, `application/rdf+xml`).

### Public Entity, Collection & Discovery Routes (Unauthenticated, `Access-Control-Allow-Origin: *`)

| Endpoint | Notes |
| --- | --- |
| `GET /api/public/works/<id>` | Work RDF (`?format=json-ld\|turtle\|nt`, `303` redirect for `text/html`) |
| `GET /api/public/expressions/<id>` | Expression RDF (`120 per minute` across single-entity routes) |
| `GET /api/public/manifestations/<id>` | Manifestation RDF |
| `GET /api/public/items/<id>` | Item RDF (`public` & non-hidden items only; owner `physical_location` redacted) |
| `GET /api/public/u/<username>/items` | User collection JSON (`page`, `per_page <= 100`) or RDF (`limit` `1..1000`, default `100`, `stream=true`) |
| `GET /api/public/feed.xml` | Global fresh arrivals RSS (`?view=works` optional, `60 per minute`) |
| `GET /api/public/sitemap.xml` | XML sitemap (`60 per minute`) |

---

## Physical Item Endpoints

### `GET /api/items/<id>`

Retrieve single physical item details including its manifestation, expression, and work.

**Authentication:** Optional (authenticated caller sees ownership and lending details; unauthenticated sees public item details unless hidden).

**Response:**

The response includes both the untouched, authoritative raw metadata in `manifestation_meta` and an additive `display` projection:

- `manifestation_meta`: Complete, unconstrained provider and OCR metadata. **Authoritative for editing and storage.** Consumers and the item editor must continue to read `manifestation_meta` for write operations.
- `display`: An additive display projection pre-computed on the server to prevent presentation duplication across UI sections:
  - `sections`: Extracted canonical sections (`format`, `description`, `categories`, `label_publisher`).
  - `fields`: Normalized field map for standard bibliographic attributes.
  - `additional_details`: Array of primitive `{ key, label, value }` entries that are not rendered in primary UI sections and pass display filters (omits empty, unknown, and structural keys).

```json
{
  "success": true,
  "data": {
    "id": 42,
    "manifestation_meta": {
      "Format": "Vinyl",
      "Publisher": "Blue Note",
      "Year": "1964",
      "CustomAttribute": "Sample"
    },
    "display": {
      "sections": {
        "format": "Vinyl",
        "label_publisher": "Blue Note"
      },
      "fields": {
        "format": "Vinyl",
        "publisher": "Blue Note"
      },
      "additional_details": [
        {
          "key": "CustomAttribute",
          "label": "CustomAttribute",
          "value": "Sample"
        }
      ]
    }
  }
}
```

### `PUT /api/items/<id>`

Update exemplar details of a physical item, including its local barcode and physical condition.

**Authentication:** Required (Item owner or administrator).

**Request Body:**

```json
{
  "local_barcode": "SHELF-01-A",
  "condition": "like_new"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": 42
  }
}
```

### `PATCH /api/items/bulk-visibility`

Atomically update the three-tier visibility level (`public`, `friends_only`, or `private` — alias `hidden` normalized to `private`) across a bounded batch of owned physical items.

**Authentication:** Required (`write:item` permission; blocked on `FEDERATION_HEAD_MODE` instances).

**Rate Limit:** 30 per minute.

**Request Body (`BulkItemVisibilitySchema`):**

- `item_ids` (`list[int]`, `1..100` positive item IDs owned by caller)
- `visibility` (`"public" | "friends_only" | "private"`)

```json
{
  "item_ids": [12, 19, 24],
  "visibility": "friends_only"
}
```

**Response (`200 OK`):**

```json
{
  "success": true,
  "data": {
    "updated_count": 3,
    "visibility": "friends_only",
    "item_ids": [12, 19, 24]
  }
}
```

Re-indexes FTS entries, invalidates facet counts, emits SSE `item_visibility_updated` events, and dispatches ActivityPub collection updates when visibility changes. Returns `404` if any requested ID is missing or not owned by the caller.

### `PATCH /api/items/bulk-location`

Atomically update `physical_location` across a bounded batch (`1..100`) of owned physical items (`BulkItemLocationSchema`).

**Authentication:** Required (`write:item` permission; blocked on `FEDERATION_HEAD_MODE` instances; returns `403 Forbidden` if any selected item is not owned by the caller).

**Rate Limit:** 30 per minute.

**Request Body:**

```json
{
  "item_ids": [12, 19, 24],
  "physical_location": "Living Room / Shelf A"
}
```

Pass `null` to clear stored shelf locations. Re-indexes FTS entries and invalidates facet caches (`location_counts`).

### `GET /api/items` Filters, Facets & Reading Sessions (`POST /api/items/<id>/reading-sessions`)

- **`GET /api/items`:** Supports comma-separated `?visibility=public,friends_only,private` and SQL-paginated `?location=...` (matching owner's `Item.physical_location`, also applied across `GET /api/items?q=...` FTS/ILIKE search and `GET /api/stats/facets?location=...`). Non-owners and unauthenticated callers never see `physical_location` in serialized items.
- **`POST /api/items/<id>/reading-sessions`:** Log an active reading session (`duration_minutes`: `1..1440`, optional `pages_read`, optional private `note`) on an owned physical item (`write:item` permission, `60 per hour`, max `200` stored sessions per item; blocked on `FEDERATION_HEAD_MODE`). Private session notes are automatically redacted from non-owner `GET /api/items/<id>` responses while durations contribute anonymously to edition averages.

---

## Manifestation Images & Reading Stats

### `GET /api/manifestations/<id>/images` & `POST /api/manifestations/<id>/images`

Retrieve or contribute gallery images (`ImageScan` rows: inlay, disc, back cover) for a Manifestation using the `{success, data, error}` envelope (`POST` requires `write:metadata`).

### `GET /api/manifestations/<id>/stats`

Return anonymized, visibility-safe `GROUP BY` reading statistics across `public`, non-hidden physical items for a Manifestation (returns `{success, data, error}`): `total_items`, `reader_count`, `completed_count`, `avg_session_minutes`, `avg_reading_days`, and monthly `popularity_over_time` (`added_count` / `completed_count` across up to 12 recent months, with zero PII or private notes).

---

## Work Shelf, Reading Rollup & Relation Graph Endpoints

### `GET /api/works/shelf`

Browse conceptual Works with aggregated user ownership, Work-level wishlist intents, and optional user-scoped Work reading progress filtering (`work_read_status`).

**Authentication:** Optional (`work_read_status` and personal annotations active when authenticated).

**Key Query Parameters:** `q`, `category`, `tags`, `collections`, `genres`, `publishers`, `statuses`, `formats`, `ownership` (`owned|not_owned`), `work_read_status` (`completed|in_progress|unread`), `limit` (`1..100`), `offset`.

### `GET /api/catalog/graph`

Return a bounded, visibility-safe FRBR neighborhood (`mode=neighborhood`) or full-library concept graph (`mode=library`) honoring `is_item_visible_to_viewer()` and `FederationConsent`.

**Authentication:** Optional (`404` on nonexistent or restricted `Item` anchor). **Rate Limit:** 60 per minute.

**Query Parameters:**

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `mode` | string | `neighborhood` | `neighborhood` or `library` |
| `entity_type` | string | Required (`neighborhood`) | `work`, `expression`, `manifestation`, `item`, `person`, `contributor`, or `series` |
| `entity_id` | integer | Required (`neighborhood`) | Positive database ID of anchor entity |
| `depth` | integer | `1` | Traversal hops (clamped `1..4`) |
| `max_nodes` | integer | `150` | Maximum nodes before truncation (`1..150`) |
| `max_edges` | integer | `400` | Maximum edges before truncation (ceiling `600`) |
| `entity_types` | CSV string | All (`library`) | `work`, `series`, `contributor`, `expression`, `manifestation`, `item`, `map`, `lod` |
| `edge_types` | CSV string | All (`7` categories) | `frbr`, `series`, `parts_expansions`, `derivatives`, `contributors`, `maps`, `lod` |

External authority URIs are canonicalized into deterministic `lod:<digest>` node IDs so intersecting LOD links across Works and Contributors merge cleanly without duplicate graph nodes.

### `GET /api/catalog/graph/search`

Diacritic-insensitive search (`?q=...&types=...&limit=10`) returning root candidates across `person`, `series`, `work`, `manifestation`, `item`, `expression`, and `contributor` (`60 per minute`).

---

## Shared Collection Scopes & AI Feeds

### `POST /api/sharing`

Create a tokenized filtered collection view with configurable `visibility_scope` and optional TTL (`expires_in_days`: `1..365`, `30 per minute`).

- `visibility_scope`:
  - `"public_only"` (default): Anonymous visitors see `public` items only; authenticated accepted friends receive the **Friend Bonus** unlocking `friends_only` items.
  - `"friends_and_public"`: Any token holder sees `public` and `friends_only` matching items (`private` stays hidden).
  - `"all"`: Any token holder sees all matching items including `private` copies.

### `GET /api/public/share/<token>` & AI Mini-Pages (`/share/<token>/jsonld/<page>`)

- Supports standard JSON (`?page=1&per_page=48`), RDF content negotiation (`Accept: application/ld+json|text/turtle|application/rdf+xml|application/n-triples`), `GET /api/public/rdf/share/<token>?format=jsonld&limit=2000` (`MAX_SHARED_COLLECTION_LIMIT=2000`), non-`/api/` `/share/<token>/catalog.jsonld` and `/share/<token>/feed.xml`, plus query-free paginated HTML/JSON-LD mini-pages `/share/<token>/jsonld/1..N` (`60` items/page) for headerless AI agents.

---

## Scanner Periodicals & Cover Vision OCR Endpoints

### `GET /api/scanner/preview/<barcode>`, `GET /api/lookup/<barcode>` & `POST /api/vision/extract`

- **`GET /api/scanner/preview/<barcode>` & `GET /api/lookup/<barcode>`:** Resolve books, audio, video, games, puzzles, LEGO sets (`570201...` / set IDs), and **Serials/Periodicals** (`977` GS1 13/15/18-digit barcodes with EAN-2/EAN-5 issue add-ons or Modulo-11 `XXXX-XXXX` ISSN) via Biblioteka Narodowa, Crossref, OpenLibrary, and Allegro. Returns existing issues for disambiguation when a bare 13-digit `977` prefix matches a cataloged periodical.
- **`POST /api/vision/extract` (`202 Accepted`) & `GET /api/vision/extract/<task_id>`:** Enqueues cover photo extraction through the 3-tier waterfall (**Gemini 2.0 Flash** -> **Ollama Vision** -> **Offline Multi-Zone Tesseract `eng+pol` Magazine OCR**) protected by a `100_000_000`-pixel Pillow decompression bomb guard, returning extracted book fields (`Title`, `Authors`, `Publisher`, `Year`, `ISBN`) and snake_case serial issue fields (`issn`, `indeks`, `issue_number`, `cumulative_issue_number`, `volume`, `publication_year`, `publication_month`, `cover_headline`).

---

## Work Series Endpoints

### `GET /api/works/<id>/series`

Retrieve all series memberships and sequence positions for a specific Work.

**Authentication:** Optional

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": 12,
      "series_work_id": 101,
      "title": "The Lord of the Rings",
      "sequence": 1
    }
  ]
}
```

### `POST /api/works/<id>/series`

Attach a Work to a container series Work with an optional sequence number.

**Authentication:** Required (`write:metadata` permission)

**Payload:**

```json
{
  "series_work_id": 101,
  "sequence": 1
}
```

### `DELETE /api/works/<id>/series/<series_work_id>`

Detach a Work from a container series Work.

**Authentication:** Required (`write:metadata` permission)

---

## Data Export & Content Negotiation

### `GET /api/items/export`

Stream export of the authenticated user's library (`format`: `json-ld` default, `turtle`, or `json`) via chunked `Transfer-Encoding`. See **[Semantic Web Guide](SEMANTIC_WEB.md)** for full curl examples, canonical `@context`, and `Accept` / `?format=` content-negotiation matrices.

---

## Federation & ActivityPub Endpoints

iQoQo supports decentralized discovery and social federation via ActivityPub, RFC 7033 WebFinger, and NodeInfo 2.1.

### `GET /.well-known/webfinger` (also `GET /api/federation/webfinger`)

Resolve user account identity and retrieve ActivityPub actor descriptors.

**Parameters:**

| Parameter  | Type   | Required | Description                                                    |
| ---------- | ------ | -------- | -------------------------------------------------------------- |
| `resource` | string | Yes      | Account query (e.g. `acct:alice@example.com` or canonical IRI) |

**Authentication:** Not required (Public). Requires user opt-in federation consent (`federated_profile: true`).

**CORS:** Wildcard `Access-Control-Allow-Origin: *`.

---

### `GET /.well-known/nodeinfo` & `GET /api/federation/nodeinfo/2.1`

Standard NodeInfo protocol describing server metadata, supported protocols, and catalog usage statistics.

**Authentication:** Not required (Public).

**CORS:** Wildcard `Access-Control-Allow-Origin: *`.

---

### `GET /api/federation/actor/u/<user_uuid>` (and `GET /api/federation/actor/<username>`)

Retrieve ActivityStreams 2.0 `Person` Actor JSON-LD representation.

**Authentication:** Not required (Public). Requires user opt-in federation consent.

**CORS:** Wildcard `Access-Control-Allow-Origin: *`.

**Response:** Contains canonical Actor IRI, `inbox`, `outbox`, and `publicKey` with PEM certificate for HTTP Signature verification.

---

### `POST /api/federation/inbox` (and `POST /api/federation/actor/u/<user_uuid>/inbox`)

Inbound ActivityPub delivery endpoint accepting signed ActivityStreams activities (e.g., `Follow`, `Undo`).

**Authentication:** Enforces `draft-cavage-12` HTTP Signatures (`(request-target)`, `host`, `date`, and `digest` when body is present). Remote public keys are fetched via SSRF-safe client.

**Protections:** Rate limited to 60 requests per minute and capped at 100KB payload limit (`413 Payload Too Large`).

---

### `GET /api/federation/lookup`

Query and discover remote federated actors by handle (`@user@domain`) or Actor URL.

**Authentication:** Required.

**Rate Limit:** 20 per minute.

---

### `POST /api/federation/follow`

Dispatch an outbound `Follow` request to a remote ActivityPub actor.

**Authentication:** Required.

**Rate Limit:** 10 per minute.

---

### `GET /api/federation/consent` & `PUT /api/federation/consent`

Retrieve or update the authenticated user's federation discovery and privacy preferences (`federated_profile`, `federated_collection`, and `auto_accept_follows`).

**Authentication:** Required.

---

### `GET /api/federation/actor/u/<user_uuid>/outbox`

Retrieve the public ActivityStreams `OrderedCollection` representing the user's outbox. Supports pagination via `page=true`.

**Authentication:** Not required (Public). Respects user's `federated_collection` and `federated_profile` consent.

---

### `GET /api/federation/actor`

Retrieve the instance `Application` actor ActivityStreams JSON-LD document publishing the server's public key (`#main-key`) for Fediverse HTTP Signatures and Authorized Fetch.

**Authentication:** Not required (Public). Returns `404 Not Found` if the instance key has not yet been provisioned.

---

### `GET /api/federation/directory`

Public directory of federated library peers with pagination and search. Non-routable internal hostnames (`localhost`, Docker bridge networks, RFC1918) are excluded.

**Authentication:** Not required (Public).

---

### `GET /api/v1/admin/federation/instances` & `POST /api/v1/admin/federation/instances`

List registered peer federation instances (including pinned `key_fingerprint` SHA-256 strings) or discover and register a new peer via NodeInfo (`/.well-known/nodeinfo`).

**Authentication:** Admin required (`role:admin` / `config:federation`).

---

### `POST /api/v1/admin/federation/key-fingerprint/provision`

Explicitly provision or rotate the local instance RSA-2048 keypair (`data/keys/server.pem`) and return the resulting `SHA256:...` fingerprint.

**Authentication:** Admin required (`role:admin` / `config:federation`). Accepts `{ "rotate": true }` to rotate an existing keypair.

---

### `PUT /api/v1/admin/federation/instances/<id>` & `DELETE /api/v1/admin/federation/instances/<id>`

Update an instance's trust level (`untrusted`, `trusted`, `blocked`) or delete an instance along with linked actors and followers.

**Authentication:** Admin required (`role:admin`).

---

### `GET /api/v1/admin/federation/activities`

Retrieve paginated audit logs of inbound and outbound federation activities with filter support by status and instance.

**Authentication:** Admin required (`role:admin`).

---

## Rate Limits

| Endpoint                              | Rate Limit          | Scope    |
| ------------------------------------- | ------------------- | -------- |
| `GET /api/sparql`                     | 10 per minute       | Per user |
| `POST /api/sparql`                    | 10 per minute       | Per user |
| `GET /api/public/works/<id>`          | 120 per minute      | Global   |
| `GET /api/public/expressions/<id>`    | 120 per minute      | Global   |
| `GET /api/public/manifestations/<id>` | 120 per minute      | Global   |
| `GET /api/public/items/<id>`          | 120 per minute      | Global   |
| `GET /api/public/feed.xml`            | 60 per minute       | Global   |
| `GET /api/public/sitemap.xml`         | 60 per minute       | Global   |
| `GET /api/items/export`               | Standard API limits | Per user |
| `GET /api/federation/lookup`          | 20 per minute       | Per user |
| `POST /api/federation/follow`         | 10 per minute       | Per user |
| `POST /api/federation/inbox`          | 60 per minute       | Global   |

When rate limited, the API returns:

```json
{
  "error": "Rate limit exceeded. Try again in X seconds.",
  "code": 429
}
```

---

## Error Responses

All error responses follow a consistent JSON envelope:

```json
{
  "error": "Human-readable error message",
  "code": 400
}
```

### SPARQL Error Codes

| Status | Error               | Cause                                    |
| ------ | ------------------- | ---------------------------------------- |
| 400    | Syntax error        | Invalid SPARQL query syntax              |
| 400    | Write rejected      | Query contains INSERT/DELETE/UPDATE      |
| 400    | Empty query         | Missing or empty query string            |
| 401    | Unauthorized        | Missing or invalid JWT token             |
| 403    | Forbidden           | User lacks `read:metadata` permission    |
| 413    | Query too large     | Query exceeds 10KB limit                 |
| 413    | Resource limit      | Result exceeds size/row/triple limits    |
| 413    | Result too large    | Serialized response exceeds 10MB         |
| 502    | Child process error | SPARQL subprocess crashed                |
| 503    | Concurrency limit   | Too many simultaneous queries (max: 4)   |
| 504    | Timeout             | Query exceeded 15-second execution limit |

### Public Endpoint Error Codes

| Status | Error     | Cause                                   |
| ------ | --------- | --------------------------------------- |
| 404    | Not found | Entity does not exist or item is hidden |

### Export Error Codes

| Status | Error          | Cause                           |
| ------ | -------------- | ------------------------------- |
| 400    | Invalid format | Unsupported export format value |
| 401    | Unauthorized   | Missing or invalid JWT token    |

---

## 📚 Further Reading

- **[Semantic Web Guide](SEMANTIC_WEB.md)** — SPARQL examples and Linked Data integration
- **[Architecture Guide](ARCHITECTURE.md)** — Semantic Web layer architecture
- **[Operations Runbook](OPERATIONS.md)** — FRBR ETL and maintenance scripts
- **[Upgrade Guide](archive/UPGRADE_0.8.0.md)** — Historical v0.8.0 migration notes
