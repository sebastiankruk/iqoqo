# Upgrading to iqoqo 0.8.0

This guide covers the breaking changes and migration steps for upgrading from 0.7.x to 0.8.0.

## Breaking Changes

### FRBR F3 Manifestation Column Promotion

Physical attributes previously stored in the JSONB `meta` column have been promoted to typed relational columns on the `Manifestation` model for better query performance and data integrity.

**Affected columns:**
- `isbn13` (VARCHAR(13)) - ISBN-13 identifier
- `publisher` (VARCHAR(255)) - Publisher name
- `format_type` (VARCHAR(50)) - Physical format (e.g., "hardcover", "paperback", "ebook")

**What changed:**
- These attributes are now first-class columns with proper indexes
- The JSONB `meta` column no longer contains these keys (they are pruned after migration)
- API responses now serialize these as top-level fields instead of nested in `meta`

### Migration Steps

The database migration (`v0_7_19_f3_column_promotion`) runs automatically when you start the new version. It:

1. **Creates new columns** with appropriate types and indexes
2. **Backfills data** from `meta` JSONB to the new columns (case-insensitive key matching)
3. **Validates data** during backfill (ISBN normalization, publisher length limits, format type validation)
4. **Prunes migrated keys** from the `meta` JSONB to avoid duplication

**For Docker deployments:**
```bash
docker compose pull
docker compose up -d
```

The migration runs automatically on startup. No manual intervention required.

**For manual deployments:**
```bash
# Apply migrations
alembic upgrade head

# Restart the application
systemctl restart iqoqo
```

### Preflight Checks

If you want to verify data quality before migrating, you can run preflight checks separately:

```python
from migrations.versions.v0_7_19_f3_column_promotion import run_preflight
from app.db import engine

with engine.connect() as conn:
    report = run_preflight(conn)
    print(report)
```

This will report:
- Invalid ISBN formats that will be normalized
- Publisher names exceeding length limits
- Invalid format types
- Case variations in meta keys (e.g., "ISBN13" vs "isbn13")

### API Changes

**Before (0.7.x):**
```json
{
  "id": 42,
  "title": "Example Book",
  "meta": {
    "isbn13": "9781234567890",
    "publisher": "Example Press",
    "format_type": "hardcover"
  }
}
```

**After (0.8.0):**
```json
{
  "id": 42,
  "title": "Example Book",
  "isbn13": "9781234567890",
  "publisher": "Example Press",
  "format_type": "hardcover",
  "meta": {}
}
```

### Custom SQL Queries

If you have custom SQL queries or reports that reference the old JSONB paths, update them to use the new columns:

**Before:**
```sql
SELECT * FROM manifestations WHERE meta->>'isbn13' = '9781234567890';
SELECT * FROM manifestations WHERE meta->>'publisher' ILIKE '%example%';
```

**After:**
```sql
SELECT * FROM manifestations WHERE isbn13 = '9781234567890';
SELECT * FROM manifestations WHERE publisher ILIKE '%example%';
```

The new columns are indexed, so queries will be significantly faster.

## New Features

### SPARQL Query Endpoint

Read-only SPARQL endpoint at `/api/sparql` supporting:
- GET requests with `?query=...` parameter
- POST requests with SPARQL in request body
- Content negotiation: SPARQL Results JSON, XML, Turtle, JSON-LD, CSV, TSV
- Rate limited to 10 queries/minute
- Requires `read:metadata` permission

### Public Linked Data Endpoints

Public RDF endpoints for AI agents and Linked Data crawlers:
- `/api/public/works/<id>`
- `/api/public/expressions/<id>`
- `/api/public/manifestations/<id>`
- `/api/public/items/<id>`

Supports JSON-LD, Turtle, N-Triples via `Accept` header or `?format=` parameter.
Open CORS headers (`Access-Control-Allow-Origin: *`).
Rate limited to 120 requests/minute per endpoint.

### Data Sovereignty Export

Export your library at `/api/items/export`:
- Formats: JSON-LD, Turtle, JSON
- Streaming response for large collections
- Authenticated users only
- FRBR-compliant hierarchical structure

### Canonical Linked Data IRIs

All entities now have stable, dereferenceable IRIs:
- `https://iqoqo.cc/works/<id>`
- `https://iqoqo.cc/expressions/<id>`
- `https://iqoqo.cc/manifestations/<id>`
- `https://iqoqo.cc/items/<id>`

Configurable via `BASE_URL` environment variable.

## Security Fixes

- **XSS Prevention**: Sanitized user-controlled strings in public profiles and shared collections
- **SSRF Safety**: Hardened URL validation on redirect headers
- **Host Header Poisoning**: Added domain validation in frontend auth routes

## Need Help?

- Check the [CHANGELOG](docs/CHANGELOG.md) for the complete list of changes
- Open an issue on [GitHub](https://github.com/sebastiankruk/iqoqo/issues)
- Review the [documentation](docs/) for detailed feature guides
