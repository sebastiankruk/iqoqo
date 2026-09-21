# Upgrading to iqoqo v0.8.0

This guide covers everything you need to know to safely upgrade from iqoqo v0.7.x to v0.8.0. Version 0.8.0 introduces the **Semantic Web layer** — SPARQL querying, Linked Open Data endpoints, canonical IRI minting, and data sovereignty exports — along with a **breaking database migration** that promotes JSONB attributes to indexed relational columns.

## 📋 Pre-Upgrade Checklist

Before upgrading, complete every item in this checklist:

### 1. Backup Your Database

```bash
# Full database dump (disaster recovery)
docker compose exec db pg_dumpall -U iqoqo > backup_pre_0.8.0.sql

# JSON export (data portability)
make db-export
```

> ⚠️ **Critical:** The F3 column promotion migration modifies the `manifestations` table. A verified backup is mandatory before proceeding.

### 2. Run Preflight Checks

```bash
# Verify database health
docker compose exec web flask db current

# Check for pending migrations
docker compose exec web flask db history

# Verify disk space (migration needs ~2x table size temporarily)
df -h
```

### 3. Review JSONB Queries

If you have custom scripts or integrations that query `Manifestation.meta` directly for `isbn13`, `publisher`, or `format_type`, note that these values are now promoted to dedicated relational columns. The API remains backward-compatible, but raw SQL queries may need updating.

```bash
# Check for JSONB references in custom scripts
grep -r "meta\['isbn" scripts/ || echo "No direct isbn13 JSONB queries found"
grep -r "meta\['publisher" scripts/ || echo "No direct publisher JSONB queries found"
grep -r "meta\['format" scripts/ || echo "No direct format_type JSONB queries found"
```

### 4. Review Environment Variables

v0.8.0 introduces `BASE_URL` for Linked Open Data IRI minting:

```bash
# Add to your .env file:
BASE_URL=https://your-domain.example.com
```

If not set, the default is `https://iqoqo.cc`. See the [Semantic Web Guide](SEMANTIC_WEB.md#iri-minting-and-base_url-configuration) for details.

## 🔄 F3 Column Promotion Explained

v0.8.0 promotes three core physical attributes from the unstructured JSONB `meta` column to indexed, typed relational columns on the `Manifestation` table:

| Attribute     | JSONB Key (old)        | Relational Column (new) | Type           | Index   |
| ------------- | ---------------------- | ----------------------- | -------------- | ------- |
| ISBN-13       | `meta['isbn13']`       | `isbn13`                | `VARCHAR(13)`  | Unique  |
| Publisher     | `meta['publisher']`    | `publisher`             | `VARCHAR(500)` | Indexed |
| Format Type   | `meta['format_type']`  | `format_type`           | `VARCHAR(50)`  | Indexed |

### Why This Matters

- **Performance:** Indexed columns enable fast faceted filtering, ISBN lookups, and publisher aggregation without JSONB parsing overhead.
- **Data Integrity:** Typed columns enforce length constraints and uniqueness (ISBN-13).
- **SPARQL & Linked Data:** Relational columns allow efficient RDF graph construction for the new Semantic Web endpoints.

### Backward Compatibility

The API serialization layer remains backward-compatible. Existing API consumers will continue to receive `isbn13`, `publisher`, and `format_type` in JSON responses. The migration backfills relational columns from existing `meta` JSONB data and prunes the redundant keys from `meta`.

## 📝 Step-by-Step Upgrade Procedure

### For Docker Deployments (Recommended)

1. **Pull the latest code:**

   ```bash
   git fetch origin
   git checkout v0.8.0
   ```

2. **Update environment variables:**

   ```bash
   # Add BASE_URL to .env if not already present
   echo "BASE_URL=https://your-domain.example.com" >> .env
   ```

3. **Stop the application services (keep database running):**

   ```bash
   docker compose stop web worker
   ```

4. **Run the database migration:**

   ```bash
   # The migration container handles this automatically on restart,
   # but you can run it explicitly for visibility:
   docker compose run --rm web flask db upgrade
   ```

   The migration (`v0_7_19_f3_column_promotion`) will:
   - Add `isbn13`, `publisher`, `format_type` columns to `manifestations`
   - Backfill values from `meta` JSONB
   - Create indexes and unique constraints
   - Prune migrated keys from `meta`

5. **Restart all services:**

   ```bash
   docker compose up -d
   ```

6. **Verify the upgrade:**

   ```bash
   # Check migration completed
   docker compose exec web flask db current

   # Verify application health
   curl -s http://localhost:8000/api/health | python3 -m json.tool

   # Test SPARQL endpoint
   curl -s "http://localhost:8000/api/sparql?query=SELECT+%2A+WHERE+%7B+%3Fs+%3Fp+%3Fo+%7D+LIMIT+1" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### For Local Development

```bash
# 1. Pull latest code
git fetch origin && git checkout v0.8.0

# 2. Update Python dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 3. Add BASE_URL to .env
echo "BASE_URL=http://localhost:5000" >> .env

# 4. Run migrations (automatic via run.sh)
./run.sh dev

# Or manually:
flask db upgrade
```

## 🔙 Rollback Procedures

If the upgrade causes issues, you can roll back:

### Database Rollback

```bash
# Rollback the F3 column promotion migration
docker compose exec web flask db downgrade

# Or restore from backup:
docker compose exec -T db psql -U iqoqo < backup_pre_0.8.0.sql
```

### Application Rollback

```bash
# Revert to previous version
git checkout v0.7.18

# Restart services
docker compose up -d
```

> **Note:** After downgrading, the `isbn13`, `publisher`, and `format_type` columns will be removed from the database. Any data that was only in the relational columns (not in `meta`) will be lost. This is why the backup step is critical.

## 🔧 Troubleshooting

### ISBN-13 Conflicts (Unique Constraint Violation)

**Symptom:** Migration fails with `duplicate key value violates unique constraint "manifestations_isbn13_key"`.

**Cause:** Multiple manifestations had the same ISBN-13 stored in their `meta` JSONB.

**Resolution:**

```bash
# 1. Identify duplicates before migration
docker compose exec db psql -U iqoqo -c "
  SELECT meta->>'isbn13' AS isbn, COUNT(*)
  FROM catalog.manifestations
  WHERE meta->>'isbn13' IS NOT NULL
  GROUP BY meta->>'isbn13'
  HAVING COUNT(*) > 1;
"

# 2. Fix duplicates (keep the first occurrence, NULL out the rest)
docker compose exec db psql -U iqoqo -c "
  UPDATE catalog.manifestations
  SET meta = meta - 'isbn13'
  WHERE id NOT IN (
    SELECT MIN(id)
    FROM catalog.manifestations
    WHERE meta->>'isbn13' IS NOT NULL
    GROUP BY meta->>'isbn13'
  )
  AND meta->>'isbn13' IS NOT NULL;
"

# 3. Retry migration
docker compose run --rm web flask db upgrade
```

### Long Publisher Names

**Symptom:** Migration warning about truncated publisher values.

**Cause:** Publisher names exceeding 500 characters.

**Resolution:** The migration truncates to `VARCHAR(500)` automatically. If you need longer publisher names, file an issue — the column size can be increased in a follow-up migration.

### Migration Takes Too Long

**Expected Duration:**

| Collection Size | Manifestations | Estimated Migration Time |
| --------------- | -------------- | ------------------------ |
| Small           | < 1,000        | < 30 seconds             |
| Medium          | 1,000 – 10,000 | 1 – 5 minutes            |
| Large           | 10,000 – 50,000| 5 – 15 minutes           |
| Very Large      | > 50,000       | 15 – 45 minutes          |

If the migration appears stuck:

```bash
# Check migration progress (in another terminal)
docker compose logs -f web | grep "f3_column_promotion"

# Check for locks
docker compose exec db psql -U iqoqo -c "
  SELECT pid, state, query, age(clock_timestamp(), query_start) AS duration
  FROM pg_stat_activity
  WHERE datname = 'iqoqo' AND state = 'active';
"
```

### SPARQL Endpoint Returns 403

**Cause:** The SPARQL endpoint requires authentication and `read:metadata` permission.

**Resolution:** Ensure you're passing a valid JWT token:

```bash
curl -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"your_password"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["access_token"])')" \
  "http://localhost:8000/api/sparql?query=SELECT+%2A+WHERE+%7B+%3Fs+%3Fp+%3Fo+%7D+LIMIT+1"
```

### BASE_URL Not Taking Effect

**Symptom:** IRIs still show `https://iqoqo.cc` after setting `BASE_URL`.

**Resolution:**

```bash
# Verify environment variable is loaded
docker compose exec web env | grep BASE_URL

# Restart the web container to pick up changes
docker compose restart web
```

## 📊 Performance Impact Analysis

### Migration Duration

The F3 column promotion migration performs a full table scan of `manifestations` to backfill relational columns from JSONB. For most deployments, this completes within minutes.

### Runtime Performance

- **SPARQL queries:** Graph construction takes 1–5 seconds for 5,000 items. Queries execute within the 15-second timeout.
- **Public Linked Data endpoints:** Response time < 100ms for single-entity lookups.
- **Data export:** Streaming export handles large collections without memory pressure.
- **Faceted navigation:** Publisher and ISBN queries are faster due to indexed columns.

### Resource Requirements

- **Memory:** SPARQL graph materialization uses up to 50MB per query for 5,000 items.
- **Disk:** The migration temporarily requires ~2x the `manifestations` table size.
- **CPU:** Migration is single-threaded; runtime SPARQL queries use subprocess isolation.

## 🔗 Further Reading

- **[CHANGELOG.md](CHANGELOG.md)** — Complete list of changes in v0.8.0
- **[SEMANTIC_WEB.md](SEMANTIC_WEB.md)** — Guide to SPARQL, Linked Data, and exports
- **[API.md](API.md)** — Full API reference for new endpoints
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Updated architecture with Semantic Web layer
- **[OPERATIONS.md](OPERATIONS.md)** — Operations runbook for FRBR ETL scripts
