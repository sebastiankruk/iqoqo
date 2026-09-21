# Upgrade Guide: v0.8.0

This guide covers the upgrade process from v0.7.18 to v0.8.0.

## Breaking Changes

### Database Migration: FRBR F3 Column Promotion

**Migration ID:** `v0_7_19_f3_column_promotion`

This migration promotes core physical attributes from the JSONB `meta` column to dedicated typed columns on the `Manifestation` model:

- `isbn13` (VARCHAR(13)) - ISBN-13 identifier
- `publisher` (VARCHAR(255)) - Publisher name  
- `format_type` (VARCHAR(50)) - Physical format type

### What Changed

**Before (v0.7.18):**

```json
{
  "id": 123,
  "title": "Example Book",
  "meta": {
    "isbn13": "978-1234567890",
    "publisher": "Example Press",
    "format_type": "hardcover"
  }
}
```

**After (v0.8.0):**

```json
{
  "id": 123,
  "title": "Example Book",
  "isbn13": "978-1234567890",
  "publisher": "Example Press",
  "format_type": "hardcover",
  "meta": {}
}
```

### Migration Process

The migration runs automatically when you start the new version. It:

1. **Creates new columns** with appropriate indexes
2. **Backfills data** from JSONB `meta` to typed columns
3. **Validates data** during backfill (ISBN normalization, length checks)
4. **Prunes migrated keys** from the JSONB `meta` column

### Preflight Checks

Before running the migration, you can perform preflight checks to identify potential issues:

```bash
# Using Docker
docker compose run --rm backend python -c "
from migrations.versions.v0_7_19_f3_column_promotion import run_preflight
from app.db import engine
with engine.connect() as conn:
    report = run_preflight(conn)
    print(report)
"

# Or directly
python -c "
from migrations.versions.v0_7_19_f3_column_promotion import run_preflight
from app.db import engine
with engine.connect() as conn:
    report = run_preflight(conn)
    print(report)
"
```

The preflight report will show:

- Invalid ISBN formats that will be normalized
- Publisher names exceeding length limits
- Invalid format types
- Case variations in JSONB keys

### Custom SQL Queries

If you have custom SQL queries or reports that reference these fields in the JSONB `meta` column, update them to use the new typed columns:

**Before:**

```sql
SELECT * FROM manifestations WHERE meta->>'isbn13' = '978-1234567890';
SELECT * FROM manifestations WHERE meta->>'publisher' ILIKE '%example%';
```

**After:**

```sql
SELECT * FROM manifestations WHERE isbn13 = '978-1234567890';
SELECT * FROM manifestations WHERE publisher ILIKE '%example%';
```

The new columns are indexed, so queries will be significantly faster.

## New Features

### SPARQL Query Endpoint

A read-only SPARQL endpoint is now available at `/api/sparql`:

```bash
# GET request
curl "https://your-iqoqo-instance/api/sparql?query=SELECT%20*%20WHERE%20%7B%20?s%20?p%20?o%20%7D%20LIMIT%2010"

# POST request
curl -X POST https://your-iqoqo-instance/api/sparql \
  -H "Content-Type: application/sparql-query" \
  -d "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

**Features:**

- Content negotiation: SPARQL Results JSON, XML, Turtle, JSON-LD, CSV, TSV
- Rate limited: 10 queries per minute
- Requires `read:metadata` permission
- Resource isolation with configurable timeout (15s default)
- Graph size limits: 5,000 items, 100,000 triples

### Public Linked Data Endpoints

Public RDF endpoints for AI agents and Linked Data crawlers:

- `/api/public/works/<id>`
- `/api/public/expressions/<id>`
- `/api/public/manifestations/<id>`
- `/api/public/items/<id>`

**Features:**

- Content negotiation: JSON-LD, Turtle, N-Triples
- Open CORS headers (`Access-Control-Allow-Origin: *`)
- Schema.org SEO metadata embedded
- Rate limited: 120 requests per minute per endpoint
- HTML requests redirect (303) to frontend page

### Data Sovereignty Export

Export your complete library in Linked Data formats:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-iqoqo-instance/api/items/export?format=jsonld"
```

**Supported formats:**

- `jsonld` - JSON-LD (default)
- `turtle` - Turtle RDF
- `json` - Hierarchical JSON

**Features:**

- Streaming export for large collections
- FRBR-compliant structure
- Includes canonical JSON-LD `@context` with FRBR, Schema.org, Dublin Core namespaces

### Canonical Linked Open Data IRIs

All entities now have stable, dereferenceable IRIs:

- `https://iqoqo.cc/works/<id>`
- `https://iqoqo.cc/expressions/<id>`
- `https://iqoqo.cc/manifestations/<id>`
- `https://iqoqo.cc/items/<id>`

The IRI base is configurable via the `BASE_URL` environment variable.

## Security Fixes

### XSS Prevention in Public Endpoints (#295)

All user-controlled strings in public profile and shared collection responses are now sanitized to prevent reflected cross-site scripting via:

- `bio` field
- `display_name` field
- Collection metadata fields

### SSRF Redirect Safety

Hardened `safe_get` in cover and HTTP client utilities with strict URL type coercion on redirect `Location` headers to prevent:

- Crashes from non-string redirect targets
- SSRF bypasses via malicious redirect chains

### Host Header Poisoning Defense

Added strict domain validation and secure fallback hosts in frontend auth exchange routes to prevent:

- Host header poisoning attacks
- Credential leakage via unvalidated `X-Forwarded-Host` headers

## Upgrade Steps

### 1. Backup Your Database

```bash
# Using the backup script
./scripts/backup.sh

# Or manually
docker compose exec postgres pg_dump -U postgres iqoqo > backup_$(date +%Y%m%d).sql
```

### 2. Pull the New Version

```bash
docker compose pull
```

### 3. Stop the Services

```bash
docker compose down
```

### 4. Start the New Version

```bash
docker compose up -d
```

The database migration will run automatically on startup. Monitor the logs:

```bash
docker compose logs -f backend
```

Look for:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will upgrade database to: v0_7_19_f3_column_promotion
INFO  [migrations.v0_7_19_f3_column_promotion] Starting F3 column promotion migration
INFO  [migrations.v0_7_19_f3_column_promotion] Backfilled X manifestations
INFO  [migrations.v0_7_19_f3_column_promotion] Migration completed successfully
```

### 5. Verify the Upgrade

```bash
# Check version
curl https://your-iqoqo-instance/api/health

# Test SPARQL endpoint
curl "https://your-iqoqo-instance/api/sparql?query=SELECT%20*%20WHERE%20%7B%20?s%20?p%20?o%20%7D%20LIMIT%201"

# Test public endpoint
curl -H "Accept: application/ld+json" \
  https://your-iqoqo-instance/api/public/works/1
```

## Troubleshooting

### Migration Fails

If the migration fails, check the logs:

```bash
docker compose logs backend | grep -i migration
```

Common issues:

- **ISBN validation errors**: The migration normalizes ISBNs automatically. Invalid ISBNs are logged but don't fail the migration.
- **Publisher name too long**: Names exceeding 255 characters are truncated and logged.
- **Invalid format type**: Invalid values are set to NULL and logged.

### Rollback

If you need to rollback to v0.7.18:

```bash
# Stop the new version
docker compose down

# Restore from backup
docker compose up -d postgres
docker compose exec -T postgres psql -U postgres iqoqo < backup_YYYYMMDD.sql
docker compose up -d
```

Note: The migration is not reversible via Alembic. You must restore from a database backup.

## Need Help?

- Check the [CHANGELOG](CHANGELOG.md) for the complete list of changes
- Review the [documentation](docs/) for detailed feature guides
- Open an issue on [GitHub](https://github.com/sebastiankruk/iqoqo/issues)
