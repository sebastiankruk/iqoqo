# 📡 API Reference

Complete reference for iqoqo's REST API endpoints, including the Semantic Web layer introduced in v0.8.0.

## Table of Contents

- [Authentication](#authentication)
- [SPARQL Endpoint](#sparql-endpoint)
- [Public Linked Data Endpoints](#public-linked-data-endpoints)
- [Data Export Endpoint](#data-export-endpoint)
- [Content Negotiation](#content-negotiation)
- [Rate Limits](#rate-limits)
- [Error Responses](#error-responses)

---

## Authentication

Most endpoints require JWT authentication. Obtain a token via:

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "your_password"
}
```json

**Response:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```json

Use the token in subsequent requests:

```bash
Authorization: Bearer eyJ...
```text

### Permission Requirements

| Endpoint Category        | Permission       | Auth Type       |
| ------------------------ | ---------------- | --------------- |
| SPARQL                   | `read:metadata`  | Required        |
| Data Export              | Any authenticated | Required        |
| Public Linked Data       | None             | Not required    |
| Public Feeds             | None             | Not required    |

---

## SPARQL Endpoint

### `GET /api/sparql`

Execute a SPARQL query via URL parameter (SPARQL Protocol compliance).

**Authentication:** Required (`read:metadata` permission)

**Parameters:**

| Parameter | Type   | Required | Description                    |
| --------- | ------ | -------- | ------------------------------ |
| `query`   | string | Yes      | URL-encoded SPARQL query string |

**Example:**

```bash
curl -G "http://localhost:8000/api/sparql" \
  --data-urlencode "query=SELECT * WHERE { ?s ?p ?o } LIMIT 5" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/sparql-results+json"
```bash

### `POST /api/sparql`

Execute a SPARQL query via request body.

**Authentication:** Required (`read:metadata` permission)

**Supported Content Types:**

| Content-Type                 | Body Format                                |
| ---------------------------- | ------------------------------------------ |
| `application/sparql-query`   | Raw SPARQL query string                    |
| `application/json`           | `{"query": "SELECT ..."}`                  |
| `application/x-www-form-urlencoded` | `query=SELECT+...` (form-encoded)   |

**Example (JSON):**

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/sparql-results+json" \
  -d '{"query": "SELECT ?title WHERE { ?work a <http://purl.org/vocab/frbr/core#Work> ; <http://purl.org/dc/terms/title> ?title } LIMIT 10"}'
```bash

**Example (Raw SPARQL):**

```bash
curl -X POST http://localhost:8000/api/sparql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-query" \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 5'
```bash

### Response Formats

#### SELECT / ASK Results

| Accept Header                      | Format               |
| ---------------------------------- | -------------------- |
| `application/sparql-results+json`  | SPARQL JSON (default)|
| `application/sparql-results+xml`   | SPARQL XML           |
| `text/csv`                         | CSV                  |
| `text/tab-separated-values`        | TSV                  |

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
```json

#### CONSTRUCT / DESCRIBE Results

| Accept Header          | Format              |
| ---------------------- | ------------------- |
| `text/turtle`          | Turtle (default)    |
| `application/ld+json`  | JSON-LD             |
| `application/rdf+xml`  | RDF/XML             |

**Turtle Response:**

```turtle
@prefix dc: <http://purl.org/dc/terms/> .
@prefix frbr: <http://purl.org/vocab/frbr/core#> .

<https://iqoqo.cc/works/42> a frbr:Work ;
    dc:title "The Hobbit" ;
    dc:creator "J.R.R. Tolkien" .
```bash

---

## Public Linked Data Endpoints

All public endpoints are **unauthenticated** and include open CORS headers for AI agents and Linked Data crawlers.

### `GET /api/public/works/<id>`

Retrieve a Work entity as RDF.

**Authentication:** Not required

**Parameters:**

| Parameter | Type   | Required | Description                            |
| --------- | ------ | -------- | -------------------------------------- |
| `format`  | string | No       | Override format: `json-ld`, `turtle`, `nt` |

**Example:**

```bash
# JSON-LD (default)
curl http://localhost:8000/api/public/works/1

# Turtle
curl -H "Accept: text/turtle" http://localhost:8000/api/public/works/1

# N-Triples via query parameter
curl "http://localhost:8000/api/public/works/1?format=nt"
```bash

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
```bash

### `GET /api/public/expressions/<id>`

Retrieve an Expression entity as RDF.

**Authentication:** Not required

```bash
curl -H "Accept: text/turtle" http://localhost:8000/api/public/expressions/3
```bash

### `GET /api/public/manifestations/<id>`

Retrieve a Manifestation entity as RDF.

**Authentication:** Not required

```bash
curl -H "Accept: application/ld+json" http://localhost:8000/api/public/manifestations/42
```bash

### `GET /api/public/items/<id>`

Retrieve an Item entity as RDF. Only non-hidden items are accessible.

**Authentication:** Not required

```bash
curl "http://localhost:8000/api/public/items/7?format=turtle"
```bash

### `GET /api/public/u/<username>/items`

Retrieve a user's public collection items.

**Authentication:** Not required

**Parameters:**

| Parameter  | Type    | Required | Description                                |
| ---------- | ------- | -------- | ------------------------------------------ |
| `format`   | string  | No       | RDF format: `json-ld`, `turtle`, `nt`      |
| `limit`    | integer | No       | Items per page (1–1000, default: 100)      |
| `stream`   | boolean | No       | Enable streaming for large collections     |
| `page`     | integer | No       | Page number (JSON mode only)               |
| `per_page` | integer | No       | Items per page (JSON mode, max: 100)       |

**Example:**

```bash
# JSON-LD collection
curl -H "Accept: application/ld+json" \
  "http://localhost:8000/api/public/u/alice/items?limit=50"

# Streaming Turtle export
curl "http://localhost:8000/api/public/u/alice/items?format=turtle&stream=true&limit=1000"

# Standard JSON (paginated)
curl "http://localhost:8000/api/public/u/alice/items?page=1&per_page=24"
```bash

### `GET /api/public/feed.xml`

Global fresh arrivals RSS feed.

```bash
curl http://localhost:8000/api/public/feed.xml
curl "http://localhost:8000/api/public/feed.xml?view=works"
```bash

### `GET /api/public/sitemap.xml`

XML sitemap for search engine indexing.

```bash
curl http://localhost:8000/api/public/sitemap.xml
```bash

### CORS Headers

All public endpoints include:

```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, OPTIONS
Access-Control-Allow-Headers: Content-Type, Accept, Authorization
```text

---

## Data Export Endpoint

### `GET /api/items/export`

Stream export of the authenticated user's library in Linked Data or JSON format.

**Authentication:** Required (any authenticated user)

**Parameters:**

| Parameter | Type   | Required | Description                                       |
| --------- | ------ | -------- | ------------------------------------------------- |
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
```bash

**Response Headers:**

```bash
Content-Type: application/ld+json  (or text/turtle, application/json)
Content-Disposition: attachment; filename="iqoqo-export-20260921-143022.jsonld"
Transfer-Encoding: chunked
```text

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
```json

---

## Content Negotiation

### Accept Headers

| Endpoint Type          | Supported Accept Headers                                        | Default             |
| ---------------------- | --------------------------------------------------------------- | ------------------- |
| SPARQL SELECT/ASK      | `application/sparql-results+json`, `+xml`, `text/csv`, `text/tab-separated-values` | SPARQL JSON         |
| SPARQL CONSTRUCT/DESCRIBE | `text/turtle`, `application/ld+json`, `application/rdf+xml` | Turtle              |
| Public Entity          | `application/ld+json`, `text/turtle`, `application/n-triples`, `text/html` | JSON-LD             |
| Public Collection      | `application/ld+json`, `text/turtle`, `application/n-triples`  | JSON-LD             |

### Format Query Parameter

As an alternative to `Accept` headers, use the `?format=` parameter:

| `?format=` Value | MIME Type                  |
| ---------------- | -------------------------- |
| `json-ld`        | `application/ld+json`      |
| `turtle`         | `text/turtle`              |
| `nt`             | `application/n-triples`    |
| `n-triples`      | `application/n-triples`    |
| `jsonld`         | `application/ld+json`      |

---

## Rate Limits

| Endpoint                          | Rate Limit        | Scope        |
| --------------------------------- | ----------------- | ------------ |
| `GET /api/sparql`                 | 10 per minute     | Per user     |
| `POST /api/sparql`                | 10 per minute     | Per user     |
| `GET /api/public/works/<id>`      | 120 per minute    | Global       |
| `GET /api/public/expressions/<id>`| 120 per minute    | Global       |
| `GET /api/public/manifestations/<id>` | 120 per minute | Global       |
| `GET /api/public/items/<id>`      | 120 per minute    | Global       |
| `GET /api/public/feed.xml`        | 60 per minute     | Global       |
| `GET /api/public/sitemap.xml`     | 60 per minute     | Global       |
| `GET /api/items/export`           | Standard API limits | Per user   |

When rate limited, the API returns:

```json
{
  "error": "Rate limit exceeded. Try again in X seconds.",
  "code": 429
}
```json

---

## Error Responses

All error responses follow a consistent JSON envelope:

```json
{
  "error": "Human-readable error message",
  "code": 400
}
```json

### SPARQL Error Codes

| Status | Error                    | Cause                                       |
| ------ | ------------------------ | ------------------------------------------- |
| 400    | Syntax error             | Invalid SPARQL query syntax                 |
| 400    | Write rejected           | Query contains INSERT/DELETE/UPDATE         |
| 400    | Empty query              | Missing or empty query string               |
| 401    | Unauthorized             | Missing or invalid JWT token                |
| 403    | Forbidden                | User lacks `read:metadata` permission       |
| 413    | Query too large          | Query exceeds 10KB limit                    |
| 413    | Resource limit           | Result exceeds size/row/triple limits       |
| 413    | Result too large         | Serialized response exceeds 10MB            |
| 502    | Child process error      | SPARQL subprocess crashed                   |
| 503    | Concurrency limit        | Too many simultaneous queries (max: 4)      |
| 504    | Timeout                  | Query exceeded 15-second execution limit    |

### Public Endpoint Error Codes

| Status | Error                    | Cause                                       |
| ------ | ------------------------ | ------------------------------------------- |
| 404    | Not found                | Entity does not exist or item is hidden     |

### Export Error Codes

| Status | Error                    | Cause                                       |
| ------ | ------------------------ | ------------------------------------------- |
| 400    | Invalid format           | Unsupported export format value             |
| 401    | Unauthorized             | Missing or invalid JWT token                |

---

## 📚 Further Reading

- **[Semantic Web Guide](SEMANTIC_WEB.md)** — SPARQL examples and Linked Data integration
- **[Architecture Guide](ARCHITECTURE.md)** — Semantic Web layer architecture
- **[Operations Runbook](OPERATIONS.md)** — FRBR ETL and maintenance scripts
- **[Upgrade Guide](UPGRADE_0.8.0.md)** — Migration instructions for v0.8.0
