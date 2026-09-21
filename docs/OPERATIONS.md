# 🛠️ Operations Runbook

This runbook covers day-to-day operational procedures for iqoqo, focusing on FRBR data integrity, ontology synchronization, and maintenance tasks introduced in v0.8.0.

## 📖 Table of Contents

- [FRBR Integrity Audit](#frbr-integrity-audit)
- [FRBR ETL Cleanup](#frbr-etl-cleanup)
- [Ontology Synchronization](#ontology-synchronization)
- [Troubleshooting FRBR Integrity Issues](#troubleshooting-frbr-integrity-issues)
- [Backup and Recovery Procedures](#backup-and-recovery-procedures)
- [Routine Maintenance Checklist](#routine-maintenance-checklist)

---

## 🔍 FRBR Integrity Audit

### `make audit-frbr`

Runs `scripts/audit_frbr_integrity.py` to check the structural integrity of the FRBR hierarchy.

### Usage

```bash
# Local development
make audit-frbr

# With JSON output and verbose logging
make audit-frbr ARGS="--json --verbose"

# Production (inside Docker container)
make audit-frbr USE_DOCKER=true

# Production with JSON output
make audit-frbr USE_DOCKER=true ARGS="--json --verbose"
```

### What It Checks

The audit script validates:

1. **Orphan Entities** — Expressions without a parent Work, Manifestations without a parent Expression, Items without a parent Manifestation.
2. **Dangling References** — Foreign key references to non-existent parent entities.
3. **ISBN Uniqueness** — Duplicate ISBN-13 values across Manifestations.
4. **Empty Works** — Works with no Expressions (dead-end hierarchy).
5. **Empty Expressions** — Expressions with no Manifestations.
6. **Column-Meta Drift** — Discrepancies between relational columns (`isbn13`, `publisher`, `format_type`) and their JSONB `meta` counterparts.

### Interpreting Output

**Standard output:**

```text
=== FRBR Integrity Audit ===
Works:           1,247
Expressions:     2,891
Manifestations:  4,562
Items:           6,789

✅ All Expressions have valid Work references
✅ All Manifestations have valid Expression references
✅ All Items have valid Manifestation references
⚠️  3 Works have no Expressions (orphan works)
⚠️  12 duplicate ISBN-13 values found
✅ Column-meta drift: 0 discrepancies
```

**JSON output (`--json`):**

```json
{
  "summary": {
    "works": 1247,
    "expressions": 2891,
    "manifestations": 4562,
    "items": 6789
  },
  "issues": [
    {
      "type": "orphan_works",
      "count": 3,
      "severity": "warning",
      "entity_ids": [42, 107, 891]
    },
    {
      "type": "duplicate_isbn",
      "count": 12,
      "severity": "warning",
      "details": [{"isbn": "9780123456789", "ids": [101, 202]}]
    }
  ],
  "status": "warnings"
}
```

### When to Run

- **After data imports:** Verify imported data maintains FRBR integrity.
- **After migrations:** Confirm schema changes didn't break relationships.
- **Scheduled (weekly):** Add to cron for ongoing monitoring.
- **Before ETL cleanup:** Establish a baseline before running destructive operations.

---

## 🧹 FRBR ETL Cleanup

### `make etl-frbr`

Runs `scripts/etl_frbr_strict.py` to perform idempotent cleanup of the FRBR data hierarchy.

### Usage

```bash
# Local development — preview changes
make etl-frbr ARGS="--dry-run --verbose"

# Local development — apply changes
make etl-frbr ARGS="--verbose"

# Production (inside Docker container)
make etl-frbr USE_DOCKER=true

# Production with dry-run
make etl-frbr USE_DOCKER=true ARGS="--dry-run --verbose"
```

### Safe vs Strict Modes

The ETL system provides two cleanup scripts:

| Script                      | Mode    | Description                                        |
| --------------------------- | ------- | -------------------------------------------------- |
| `scripts/etl_frbr_strict.py`| Strict  | Removes orphan entities, deduplicates ISBNs, prunes empty hierarchies |
| `scripts/etl_frbr_safe.py`  | Safe    | Non-destructive — only reports issues, never deletes |

> **Note:** `make etl-frbr` runs the **strict** mode. Use `scripts/etl_frbr_safe.py` directly for safe/audit-only mode.

### What Strict Mode Does

1. **Remove Orphan Works** — Deletes Works with zero Expressions (after verifying no Items reference them).
2. **Remove Orphan Expressions** — Deletes Expressions with zero Manifestations.
3. **Deduplicate ISBNs** — For duplicate ISBN-13 values, keeps the most recently updated Manifestation and NULLs out the duplicates.
4. **Prune Empty Meta** — Removes empty JSONB `meta` dictionaries (`{}`) to reduce storage.
5. **Normalize NULL Formats** — Sets consistent NULL values for missing format data.

### Safety Precautions

- **Always dry-run first:** `make etl-frbr ARGS="--dry-run --verbose"` shows what would change without modifying data.
- **Backup before applying:** Run `make db-export` before executing without `--dry-run`.
- **Idempotent:** Running the ETL multiple times produces the same result — safe to re-run.
- **Transactional:** All changes are wrapped in database transactions; failures roll back completely.

### Example Workflow

```bash
# 1. Audit first
make audit-frbr ARGS="--json"

# 2. Preview ETL changes
make etl-frbr ARGS="--dry-run --verbose"

# 3. Backup
make db-export

# 4. Apply ETL
make etl-frbr USE_DOCKER=true ARGS="--verbose"

# 5. Verify
make audit-frbr ARGS="--json"
```

---

## 🔄 Ontology Synchronization

### `make sync-ontology`

Runs `scripts/sync_ontology.py` to verify that the OWL ontology (`docs/ontology/iqoqo.ttl`) and SHACL shapes (`docs/ontology/iqoqo-shapes.ttl`) are synchronized with the current database schema.

### Usage

```bash
# Check mode (CI-friendly, exits non-zero on drift)
make sync-ontology ARGS="--check"

# Verbose check
make sync-ontology ARGS="--check --verbose"

# Production
make sync-ontology USE_DOCKER=true ARGS="--check"

# Sync mode (updates ontology to match schema)
make sync-ontology
```

### What It Checks

1. **Class Coverage** — Every database model (Work, Expression, Manifestation, Item, etc.) has a corresponding OWL class.
2. **Property Coverage** — Every relational column has a corresponding OWL object or data property.
3. **SHACL Shape Alignment** — SHACL constraint shapes match database constraints (NOT NULL, UNIQUE, CHECK).
4. **Namespace Consistency** — All namespace prefixes are correctly bound and used.

### CI Integration

Use `--check` mode in CI pipelines to catch ontology drift:

```yaml
# Example GitHub Actions step
- name: Verify ontology sync
  run: make sync-ontology ARGS="--check"
```

If the check fails, the ontology needs to be updated to reflect recent schema changes.

### When to Run

- **After schema changes:** Any time you add/modify database models or columns.
- **Before releases:** Verify ontology is current.
- **CI pipeline:** Automated check on every pull request.

---

## 🔧 Troubleshooting FRBR Integrity Issues

### Orphan Works (Works Without Expressions)

**Symptom:** Audit reports "N Works have no Expressions."

**Cause:** Usually caused by incomplete data imports or manual database edits.

**Resolution:**

```bash
# Option 1: Remove orphan works (if they have no useful data)
make etl-frbr ARGS="--verbose"

# Option 2: Investigate specific orphans
docker compose exec db psql -U iqoqo -c "
  SELECT w.id, w.title, w.meta->>'authors' AS authors
  FROM catalog.works w
  LEFT JOIN catalog.expressions e ON e.work_id = w.id
  WHERE e.id IS NULL;
"
```

### Duplicate ISBN-13 Values

**Symptom:** Audit reports "N duplicate ISBN-13 values found."

**Cause:** Multiple manifestations imported with the same ISBN (e.g., different printings sharing an ISBN).

**Resolution:**

```bash
# View duplicates
docker compose exec db psql -U iqoqo -c "
  SELECT isbn13, COUNT(*) AS count, array_agg(id) AS manifestation_ids
  FROM catalog.manifestations
  WHERE isbn13 IS NOT NULL
  GROUP BY isbn13
  HAVING COUNT(*) > 1
  ORDER BY count DESC;
"

# ETL strict mode will deduplicate (keeps most recent)
make etl-frbr ARGS="--dry-run --verbose"  # Preview first
make etl-frbr ARGS="--verbose"            # Apply
```

### Column-Meta Drift

**Symptom:** Audit reports "N column-meta drift discrepancies."

**Cause:** Relational columns (`isbn13`, `publisher`, `format_type`) don't match their JSONB `meta` counterparts. This can happen if data was updated through one path but not the other.

**Resolution:**

```bash
# View drift details
docker compose exec db psql -U iqoqo -c "
  SELECT id, isbn13 AS col_isbn, meta->>'isbn13' AS meta_isbn
  FROM catalog.manifestations
  WHERE isbn13 IS DISTINCT FROM meta->>'isbn13'
  LIMIT 20;
"

# The ETL process reconciles drift automatically
make etl-frbr ARGS="--verbose"
```

### SPARQL Query Timeouts

**Symptom:** SPARQL queries return HTTP 504 (Gateway Timeout).

**Cause:** Complex queries on large collections exceeding the 15-second timeout.

**Resolution:**

1. **Simplify the query:** Add `LIMIT` clauses, reduce `FILTER` complexity.
2. **Reduce graph size:** The SPARQL endpoint materializes up to 5,000 items. Large collections may produce complex graphs.
3. **Check concurrency:** If 4 queries are already running, new queries wait. Check server logs for concurrency limit rejections.

```bash
# Check server logs for SPARQL issues
docker compose logs web | grep "SPARQL"
```

---

## 💾 Backup and Recovery Procedures

### Pre-Maintenance Backup

Always backup before running ETL or migration operations:

```bash
# 1. Full database dump
docker compose exec db pg_dumpall -U iqoqo > backup_$(date +%Y%m%d).sql

# 2. JSON export (portable)
make db-export

# 3. Verify backup
wc -l backup_$(date +%Y%m%d).sql
ls -lh exports/backup.json
```

### Recovery from Backup

```bash
# Restore from SQL dump
docker compose exec -T db psql -U iqoqo < backup_20260921.sql

# Or restore from JSON export
docker compose exec web python scripts/init_db.py --seed-file exports/backup.json
```

### Automated Backup Schedule

For production deployments, schedule regular backups:

```bash
# Install daily backup cron (03:00)
make backup-install remote=<rclone_remote_name>

# Verify backup health
make backup-check remote=<rclone_remote_name>

# Manual backup run
make backup-run remote=<rclone_remote_name>
```

See [BACKUPS.md](BACKUPS.md) for multi-tier backup configuration (daily sync + S3 Glacier cold archiving).

---

## 📋 Routine Maintenance Checklist

### Daily

- [ ] Check application health: `curl http://localhost:8000/api/health`
- [ ] Review error logs: `docker compose logs --since=24h web | grep ERROR`
- [ ] Verify backup freshness: `make backup-check remote=<name>`

### Weekly

- [ ] Run FRBR integrity audit: `make audit-frbr USE_DOCKER=true ARGS="--json"`
- [ ] Check SPARQL endpoint: Test a simple query with authentication
- [ ] Review disk usage: `df -h` and `docker system df`

### Monthly

- [ ] Run ETL cleanup (after backup): `make etl-frbr USE_DOCKER=true`
- [ ] Verify ontology sync: `make sync-ontology USE_DOCKER=true ARGS="--check"`
- [ ] Update Python dependencies: `pip install -r requirements.txt --upgrade`
- [ ] Review and rotate logs

### Quarterly

- [ ] Full disaster recovery test: Restore from backup to a staging environment
- [ ] Review and update SHACL shapes if schema changed
- [ ] Audit user permissions and roles
- [ ] Review and update `shared/format_mappings.yaml`

---

## 📚 Further Reading

- **[Semantic Web Guide](SEMANTIC_WEB.md)** — SPARQL queries and Linked Data endpoints
- **[Architecture Guide](ARCHITECTURE.md)** — System architecture and data model
- **[Upgrade Guide](UPGRADE_0.8.0.md)** — Version migration procedures
- **[API Reference](API.md)** — Endpoint documentation
- **[iqoqo Ontology](ontology/iqoqo.ttl)** — OWL ontology file
- **[SHACL Shapes](ontology/iqoqo-shapes.ttl)** — Constraint validation shapes
