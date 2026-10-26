# 📡 API Reference

Complete reference for iqoqo's REST API endpoints, including the Semantic Web layer introduced in v0.8.0.

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

- `GET /api/auth/2fa/status` — Check whether TOTP is enabled and retrieve remaining recovery code count.
- `POST /api/auth/2fa/enroll` — Begin TOTP setup; returns base32 secret, provisioning URI, and SVG QR code.
- `POST /api/auth/2fa/verify` — Verify the 6-digit TOTP code and activate 2FA; returns 8 single-use recovery codes.
- `DELETE /api/auth/2fa/disable` — Disable TOTP (requires current password or valid TOTP code).

When 2FA is enabled on an account, `POST /api/auth/login` returns:

```json
{
  "success": true,
  "mfa_required": true,
  "user_id": "018f...-uuid"
}
```

The client must submit the second factor to `POST /api/auth/login/challenge` with the 6-digit `code` (or a recovery code) to obtain the JWT session tokens.

### Real-Time Transition Events (SSE Stream)

Asynchronous entity transitions and background full-text search indexing updates are streamed in real time via Server-Sent Events (SSE):

```http
GET /api/v1/events/stream
Authorization: Bearer <session_jwt>
Accept: text/event-stream
```

Streams emit typed transition events:

```text
event: transition
data: {"event": "item_transition", "entity_type": "item", "entity_id": 42, "user_id": 1, "timestamp": 1729940400}
```

Events are strictly isolated by `user_id` to prevent cross-tenant event leakage. Clients disconnect cleanly using standard EventSource lifecycles.

### OpenAPI 3.1 & Interactive Documentation

- **OpenAPI 3.1 Spec (JSON):** `GET /api/docs/openapi.json`
- **Interactive Swagger UI:** `GET /api/docs/swagger`
- Covers 100% of application routes, security schemes (`BearerAuth`, `PersonalAccessToken`, `DeployToken`), and FRBR component schemas.

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

## SPARQL Endpoint

### `GET /api/sparql`

Execute a SPARQL query via URL parameter (SPARQL Protocol compliance).

**Authentication:** Required (`read:metadata` permission)

**Parameters:**

| Parameter | Type   | Required | Description                     |
| --------- | ------ | -------- | ------------------------------- |
| `query`   | string | Yes      | URL-encoded SPARQL query string |

**Example:**

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 5" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/sparql-results+json"
```

### `POST /api/sparql`

Execute a SPARQL query via request body.

**Authentication:** Required (`read:metadata` permission)

**Supported Content Types:**

| Content-Type                        | Body Format                       |
| ----------------------------------- | --------------------------------- |
| `application/sparql-query`          | Raw SPARQL query string           |
| `application/json`                  | `{"query": "SELECT ..."}`         |
| `application/x-www-form-urlencoded` | `query=SELECT+...` (form-encoded) |

**Example (JSON):**

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/sparql-results+json" \
  -d '{"query": "SELECT ?title WHERE { ?work a <http://purl.org/vocab/frbr/core#Work> ; <http://purl.org/dc/terms/title> ?title } LIMIT 10"}'
```

**Example (Raw SPARQL):**

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-query" \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 5'
```

### Response Formats

#### SELECT / ASK Results

| Accept Header                     | Format                |
| --------------------------------- | --------------------- |
| `application/sparql-results+json` | SPARQL JSON (default) |
| `application/sparql-results+xml`  | SPARQL XML            |
| `text/csv`                        | CSV                   |
| `text/tab-separated-values`       | TSV                   |

**SPARQL JSON Response:**

```json
{
  "head": { "vars": ["title", "author"] },
  "results": {
    "bindings": [
      {
        "title": { "type": "literal", "value": "The Hobbit" },
        "author": { "type": "literal", "value": "J.R.R. Tolkien" }
      }
    ]
  }
}
```

#### CONSTRUCT / DESCRIBE Results

| Accept Header         | Format           |
| --------------------- | ---------------- |
| `text/turtle`         | Turtle (default) |
| `application/ld+json` | JSON-LD          |
| `application/rdf+xml` | RDF/XML          |

**Turtle Response:**

```turtle
@prefix dc: <http://purl.org/dc/terms/> .
@prefix frbr: <http://purl.org/vocab/frbr/core#> .

<https://iqoqo.cc/works/42> a frbr:Work ;
    dc:title "The Hobbit" ;
    dc:creator "J.R.R. Tolkien" .
```

---

## Public Linked Data Endpoints

All public endpoints are **unauthenticated** and include open CORS headers for AI agents and Linked Data crawlers.

### `GET /api/public/works/<id>`

Retrieve a Work entity as RDF.

**Authentication:** Not required

**Parameters:**

| Parameter | Type   | Required | Description                                |
| --------- | ------ | -------- | ------------------------------------------ |
| `format`  | string | No       | Override format: `json-ld`, `turtle`, `nt` |

**Example:**

```bash
# JSON-LD (default)
curl http://localhost:8000/api/public/works/1

# Turtle
curl -H "Accept: text/turtle" http://localhost:8000/api/public/works/1

# N-Triples via query parameter
curl "http://localhost:8000/api/public/works/1?format=nt"
```

**Response (JSON-LD):**

```json
{
  "@context": {
    "frbr": "http://purl.org/vocab/frbr/core#",
    "dc": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/"
  },
  "@id": "https://iqoqo.cc/works/1",
  "@type": "frbr:Work",
  "dc:title": "The Hobbit",
  "dc:creator": "J.R.R. Tolkien"
}
```

### `GET /api/public/expressions/<id>`

Retrieve an Expression entity as RDF.

**Authentication:** Not required

```bash
curl -H "Accept: text/turtle" http://localhost:8000/api/public/expressions/3
```

### `GET /api/public/manifestations/<id>`

Retrieve a Manifestation entity as RDF.

**Authentication:** Not required

```bash
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/manifestations/42
```

### `GET /api/public/items/<id>`

Retrieve an Item entity as RDF. Only non-hidden items are accessible.

**Authentication:** Not required

```bash
curl "http://localhost:8000/api/public/items/7?format=turtle"
```

### `GET /api/public/u/<username>/items`

Retrieve a user's public collection items.

**Authentication:** Not required

**Parameters:**

| Parameter  | Type    | Required | Description                            |
| ---------- | ------- | -------- | -------------------------------------- |
| `format`   | string  | No       | RDF format: `json-ld`, `turtle`, `nt`  |
| `limit`    | integer | No       | Items per page (1–1000, default: 100)  |
| `stream`   | boolean | No       | Enable streaming for large collections |
| `page`     | integer | No       | Page number (JSON mode only)           |
| `per_page` | integer | No       | Items per page (JSON mode, max: 100)   |

**Example:**

```bash
# JSON-LD collection
curl -H "Accept: application/ld+json" \
  "http://localhost:8000/api/public/u/alice/items?limit=50"

# Streaming Turtle export
curl "http://localhost:8000/api/public/u/alice/items?format=turtle&stream=true&limit=1000"

# Standard JSON (paginated)
curl "http://localhost:8000/api/public/u/alice/items?page=1&per_page=24"
```

### `GET /api/public/feed.xml`

Global fresh arrivals RSS feed.

```bash
curl http://localhost:8000/api/public/feed.xml
curl "http://localhost:8000/api/public/feed.xml?view=works"
```

### `GET /api/public/sitemap.xml`

XML sitemap for search engine indexing.

```bash
curl http://localhost:8000/api/public/sitemap.xml
```

### CORS Headers

All public endpoints include:

```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, OPTIONS
Access-Control-Allow-Headers: Content-Type, Accept, Authorization
```

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

## Data Export Endpoint

### `GET /api/items/export`

Stream export of the authenticated user's library in Linked Data or JSON format.

**Authentication:** Required (any authenticated user)

**Parameters:**

| Parameter | Type   | Required | Description                                          |
| --------- | ------ | -------- | ---------------------------------------------------- |
| `format`  | string | No       | Export format: `json-ld` (default), `turtle`, `json` |

**Example:**

```bash
# JSON-LD export (default)
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.jsonld \
  "http://localhost:8000/api/items/export"

# Turtle export
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.ttl \
  "http://localhost:8000/api/items/export?format=turtle"

# JSON export
curl -H "Authorization: Bearer $TOKEN" \
  -o my-library.json \
  "http://localhost:8000/api/items/export?format=json"
```

**Response Headers:**

```http
Content-Type: application/ld+json  (or text/turtle, application/json)
Content-Disposition: attachment; filename="iqoqo-export-20260921-143022.jsonld"
Transfer-Encoding: chunked
```

### Format Details

#### JSON-LD (`application/ld+json`)

Includes canonical `@context` with FRBR, Schema.org, Dublin Core, and iqoqo ontology namespace mappings. Each item is a JSON-LD resource with typed properties.

#### Turtle (`text/turtle`)

Standard W3C RDF Turtle serialization with prefixed namespaces (`frbr:`, `schema:`, `dc:`, `iqoqo:`).

#### JSON (`application/json`)

Hierarchical JSON following the FRBR Group 1 structure:

```json
{
  "version": "1.0",
  "exported_at": "2026-09-21T14:30:22.000000",
  "items": [
    {
      "id": 1,
      "status": "available",
      "manifestation": {
        "id": 42,
        "isbn13": "9780547928227",
        "publisher": "Mariner Books",
        "expression": {
          "id": 17,
          "language": "en",
          "work": {
            "id": 1,
            "title": "The Hobbit"
          }
        }
      }
    }
  ]
}
```

---

## Content Negotiation

### Accept Headers

| Endpoint Type             | Supported Accept Headers                                                           | Default     |
| ------------------------- | ---------------------------------------------------------------------------------- | ----------- |
| SPARQL SELECT/ASK         | `application/sparql-results+json`, `+xml`, `text/csv`, `text/tab-separated-values` | SPARQL JSON |
| SPARQL CONSTRUCT/DESCRIBE | `text/turtle`, `application/ld+json`, `application/rdf+xml`                        | Turtle      |
| Public Entity             | `application/ld+json`, `text/turtle`, `application/n-triples`, `text/html`         | JSON-LD     |
| Public Collection         | `application/ld+json`, `text/turtle`, `application/n-triples`                      | JSON-LD     |

### Format Query Parameter

As an alternative to `Accept` headers, use the `?format=` parameter:

| `?format=` Value | MIME Type               |
| ---------------- | ----------------------- |
| `json-ld`        | `application/ld+json`   |
| `turtle`         | `text/turtle`           |
| `nt`             | `application/n-triples` |
| `n-triples`      | `application/n-triples` |
| `jsonld`         | `application/ld+json`   |

---

## Federation & ActivityPub Endpoints

Introduced in **v0.9.0**, iQoQo supports decentralized discovery and social federation via ActivityPub, RFC 7033 WebFinger, and NodeInfo 2.1.

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

Retrieve or update the authenticated user's federation discovery preferences (`federated_profile` and `federated_collection`).

**Authentication:** Required.

---

### `GET /api/federation/actor/u/<user_uuid>/outbox`

Retrieve the public ActivityStreams `OrderedCollection` representing the user's outbox. Supports pagination via `page=true`.

**Authentication:** Not required (Public). Respects user's `federated_collection` and `federated_profile` consent.

---

### `GET /api/v1/admin/federation/instances` & `POST /api/v1/admin/federation/instances`

List registered peer federation instances or discover and register a new peer via NodeInfo (`/.well-known/nodeinfo`).

**Authentication:** Admin required (`role:admin`).

---

### `PUT /api/v1/admin/federation/instances/<id>` & `DELETE /api/v1/admin/federation/instances/<id>`

Update an instance's trust level (`untrusted`, `pending`, `trusted`, `blocked`) or delete an instance along with linked actors and followers.

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
- **[Upgrade Guide](UPGRADE_0.8.0.md)** — Migration instructions for v0.8.0
