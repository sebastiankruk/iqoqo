# Technical Design: v0.8.4 Release Review Findings Sweep

## Context

During the pre-release review of `release/0.8.3` (PR #329), five minor (🟢 LOW) findings were identified across frontend rendering, operational CLI tooling, network security, proxy timeouts, and configuration healthchecks. See `proposal.md` for motivation.

## Goals / Non-Goals

**Goals:**
- Eliminate raw HTML emission during Next.js SSR passes in `RichText`.
- Modernize `scripts/repair_frbr_authors.py` with SQLAlchemy 2.0 and eliminate N+1 queries with constant heap memory.
- Eliminate insecure plaintext HTTP fallback for external gazetteer downloads.
- Align reverse proxy timeout configurations with SPARQL execution service deadline budgets.
- Add production secret checks for the SPARQL execution service in `iqoqo-status.sh`.

**Non-Goals:**
- Re-architecting the SPARQL protocol or query parser.
- Modifying FRBR ontology models or adding database migrations.
- Reworking catalog search or frontend editor state management.

## Decisions

### Decision 1: SSR HTML Safety in `RichText`
- **Approach:** In `frontend/components/ui/rich-text.tsx`, update `sanitizeRichHtml`:
  - When `typeof window === "undefined"`, strip HTML tags to plain text or defer raw HTML rendering until mounted on the client (`isMounted` state guard).
  - On the client after mount, continue using configured `DOMPurify` with allowed tag/attribute whitelists.
- **Rationale:** Prevents un-sanitized HTML from ever being output into the SSR payload while ensuring client hydration renders the sanitized rich text smoothly.
- **Alternatives Considered:** Importing `isomorphic-dompurify`. Rejected to avoid introducing heavy Node.js JSDOM dependencies into client-bundle build pipelines.

### Decision 2: SQLAlchemy 2.0 Batching & Eager Loading in `repair_frbr_authors.py`
- **Approach:**
  - Replace `Work.query.all()` with `select(Work).options(selectinload(Work.contributions)).order_by(Work.id)`.
  - Stream results using `.execution_options(yield_per=500)` or keyset chunks.
  - Access `work.contributions` relationship in-memory rather than querying `WorkContribution.query.filter_by(work_id=work.id).all()` on every iteration.
  - Commit updates in incremental batches.
- **Rationale:** Complies with repository ORM rules (SQLAlchemy 2.0 style syntax, no legacy `Query`, no unbounded memory dumps).

### Decision 3: Enforce TLS & Checksum for GeoNames Gazetteer
- **Approach:**
  - Remove `FALLBACK_HTTP_URL` in `scripts/init_geonames_db.py`.
  - Disallow downloads over plain HTTP; require HTTPS strictly.
  - Add optional SHA-256 validation support via `--sha256` parameter.
- **Rationale:** Eliminates MITM injection risks when setting up or updating geographic reference databases.

### Decision 4: Align Upstream Proxy Read Timeouts
- **Approach:**
  - In `deploy/nginx.conf.example`, explicitly configure `proxy_read_timeout 45s;` and `proxy_connect_timeout 10s;` for the `/api/sparql` route.
  - Document the deadline budget: 30s query execution + 5s HTTP client buffer + 10s proxy margin.
- **Rationale:** Ensures long queries return structured `504` JSON envelopes from the application instead of abrupt `502 Bad Gateway` drops by Nginx.

### Decision 5: Production Secret Check in `iqoqo-status.sh`
- **Approach:**
  - In `scripts/iqoqo-status.sh`, inspect `SPARQL_SERVICE_SECRET`.
  - If `FLASK_ENV == "production"` or `--deploy-dir` is active, verify that `SPARQL_SERVICE_SECRET` is set and not equal to `"dev-sparql-service-secret"`.
- **Rationale:** Protects internal execution endpoints against default credential reuse across production instances.

## Risks / Trade-offs

- **[Risk]** Client hydration mismatch in Next.js if SSR renders plain text while client renders rich HTML.  
  → **Mitigation:** Use `suppressHydrationWarning` on the RichText wrapper or render a loading skeleton/plain text container until hydration completes.
- **[Risk]** Large transaction logs if all works are committed at once in `repair_frbr_authors.py`.  
  → **Mitigation:** Batch commits every 100 repaired records.
