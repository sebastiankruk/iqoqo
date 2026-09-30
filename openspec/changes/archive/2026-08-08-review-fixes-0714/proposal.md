## Why

PR #208 (`release/0.7.14`) was reviewed by 8 specialized team reviewers (Dev, Onto, PM, QA, Security, SRE, TechComm, UX) plus GitHub Copilot. The consolidated review identified 12 CRITICAL and 7 IMPORTANT issues that **must be fixed before merging to `main`**. These span security vulnerabilities (SSRF redirect bypass, DNS rebinding, broken auth), data integrity bugs (barcode truncation, migration row-skip), performance regressions (cache key fragmentation), documentation gaps, and UX clutter regressions.

## What Changes

- **Security**: Fix SSRF redirect bypass (`allow_redirects=False` + manual redirect loop), fix HTTPS DNS rebinding TOCTOU, add `@admin_required` to Allegro OAuth endpoints, add rate limiting to barcode preview
- **Data Integrity**: Remove barcode silent truncation, fix cache key normalization (sort query params), fix Alembic migration backfill row-skip bug
- **Infrastructure**: Harden `.dockerignore` to exclude secrets, fix duplicate rclone upload in AI covers
- **Documentation**: Restore stripped TSDoc comments, set CHANGELOG release date, update README version references
- **UX**: Fix InstanceSettings button density, consolidate FRBR Editor action bars into overflow menus, add scanner camera viewfinder processing overlay
- **Testing**: Fix E2E screenshot flakiness (`networkidle`), add Allegro OAuth device flow frontend tests

## Capabilities

### New Capabilities

- `ssrf-redirect-protection`: Prevent SSRF via HTTP 302 redirect chaining and DNS rebinding with socket-level IP pinning
- `review-fixes-data-integrity`: Fix barcode truncation, cache key normalization, and migration backfill bugs
- `review-fixes-docker-hardening`: Harden `.dockerignore` and fix duplicate rclone uploads
- `review-fixes-docs`: Restore TSDoc, finalize CHANGELOG date, update README versions
- `review-fixes-ux-clutter`: Fix InstanceSettings button density, FRBR Editor action bars, camera viewfinder overlay
- `review-fixes-auth-security`: Enforce admin-only access on Allegro OAuth and rate-limit barcode preview
- `review-fixes-test-stability`: Fix E2E screenshot flakiness and add Allegro OAuth component tests

### Modified Capabilities

- `ssrf-prevention`: Extending SSRF protection to cover redirect chains and HTTPS DNS rebinding
- `xxe-prevention`: Ensuring complete `defusedxml` migration (verification pass)

## Impact

- **Backend**: `app/utils/http_client.py`, `app/utils/llm_covers.py`, `app/api/scanner.py`, `app/api/auth.py`, `app/core/cache.py`, `app/api/system.py`, `migrations/versions/e3f891ab45c2_*.py`
- **Frontend**: `frontend/components/admin/instance-settings.tsx`, `frontend/components/admin/frbr-editor.tsx`, `frontend/components/scanner/camera-capture.tsx`, `frontend/__tests__/e2e/ux_audit.spec.ts`
- **Infra**: `.dockerignore`, `docs/CHANGELOG.md`, `README.md`
- **Testing**: New test files for Allegro OAuth flow, modified E2E wait strategies
