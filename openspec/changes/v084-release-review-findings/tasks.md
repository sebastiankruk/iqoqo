## 1. Frontend RichText SSR Sanitization

- [ ] 1.1 Update `frontend/components/ui/rich-text.tsx` to safely handle SSR passes by stripping tags or deferring raw HTML rendering when DOMPurify window context is missing, and verify with `npm --prefix frontend test -- --run __tests__/components/ui/rich-text.test.tsx`
- [ ] 1.2 Add an SSR unit test to `frontend/__tests__/components/ui/rich-text.test.tsx` verifying that un-sanitized HTML tags and script payloads are neutralized when `window` is undefined

## 2. Operational Author Repair Script Modernization

- [ ] 2.1 Refactor `scripts/repair_frbr_authors.py` to use SQLAlchemy 2.0 `select(Work)` with `selectinload(Work.contributions)` and batch streaming instead of legacy `Work.query.all()`, ensuring constant heap memory usage
- [ ] 2.2 Eliminate inner `WorkContribution.query.filter_by` N+1 queries by accessing preloaded contributions in memory, and verify behavior with `pytest tests/test_frbr_author_normalization.py`

## 3. Network Integrity & GeoNames Gazetteer Ingestion

- [ ] 3.1 Remove cleartext HTTP fallback in `scripts/init_geonames_db.py`, enforcing HTTPS-only downloads for the GeoNames cities gazetteer
- [ ] 3.2 Add optional SHA-256 integrity checksum verification to `scripts/init_geonames_db.py` and verify via CLI invocation

## 4. Reverse Proxy Timeouts & Production Healthchecks

- [ ] 4.1 Update `deploy/nginx.conf.example` with `proxy_read_timeout 45s;` to accommodate 30s maximum SPARQL query deadlines plus client buffers
- [ ] 4.2 Update `scripts/iqoqo-status.sh` to validate that `SPARQL_SERVICE_SECRET` is non-default when running in production mode, and verify with `bats tests/bash/iqoqo_status.bats`
