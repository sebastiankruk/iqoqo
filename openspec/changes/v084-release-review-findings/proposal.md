# Proposal: Address Findings from v0.8.3 Release Review

## Why

Comprehensive pre-release review of `release/0.8.3` (PR #329) identified five low-severity (🟢 LOW) maintainability, performance, security defense-in-depth, and operational hardening findings. While none blocked the promotion of v0.8.3, resolving them in v0.8.4 ensures long-term architectural health, constant-memory CLI maintenance operations, secure gazetteer synchronization, and resilient reverse proxy and SSR behavior.

## What Changes

- **LOW-SEC-1 (Frontend / SSR Sanitization):** Enhance `RichText` in `frontend/components/ui/rich-text.tsx` to safely handle server-side rendering (SSR) passes when DOMPurify's browser DOM instance is unavailable, preventing un-sanitized HTML emission during initial Next.js server passes.
- **LOW-SRE-1 (CLI / Memory & N+1 Queries):** Refactor `scripts/repair_frbr_authors.py` from legacy `Work.query.all()` to SQLAlchemy 2.0 `select(Work)` with eager loading (`selectinload(Work.contributions)`) and batch execution (`yield_per(500)`), eliminating full-table memory loading and N+1 query loops.
- **LOW-SEC-2 (Operations / Network Integrity):** Enforce HTTPS and add SHA-256 integrity verification to GeoNames gazetteer dump downloads in `scripts/init_geonames_db.py`, eliminating insecure cleartext HTTP fallback.
- **LOW-OPS-1 (DevOps / Proxy Timeouts):** Document and align reverse proxy timeouts (e.g. `proxy_read_timeout 45s` in `deploy/nginx.conf.example`) to accommodate the maximum 30s SPARQL execution service deadline plus client transport buffer.
- **LOW-SEC-3 (Security / Healthchecks):** Add production healthcheck validation in `scripts/iqoqo-status.sh` ensuring `SPARQL_SERVICE_SECRET` is explicitly configured with a non-default secret when running in production mode.

## Capabilities

### New Capabilities
None

### Modified Capabilities
None (`skip_specs: true` has been set in `.openspec.yaml`).

## Impact

- Closes all remaining findings logged during the v0.8.3 release review.
- Strengthens SSR security defense-in-depth for catalog descriptions.
- Ensures scalability and memory bounds for large-scale catalog metadata repair scripts.
- Protects offline gazetteer synchronization against network tampering.
- Prevents premature reverse proxy disconnects during complex read-only SPARQL evaluations.
