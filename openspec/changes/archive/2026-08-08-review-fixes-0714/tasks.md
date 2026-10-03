## 1. Security: SSRF Redirect Chain & DNS Rebinding Fix

- [x] 1.1 Add `allow_redirects=False` to `requests.get()` call in `safe_get()` (`app/utils/http_client.py`)
- [x] 1.2 Implement manual redirect loop (max 5 hops) with DNS re-resolution and `is_ip_blocked()` check on each hop
- [x] 1.3 Implement `SSRFProtectionAdapter` with `PinningHTTPSConnection` for socket-level IP pinning on HTTPS
- [x] 1.4 Update `safe_get()` docstring to accurately reflect redirect and DNS rebinding protections
- [x] 1.5 Add pytest tests for redirect-chain SSRF and DNS-rebinding scenarios in `tests/test_http_client.py`

## 2. Security: Auth Hardening

- [x] 2.1 Add `@admin_required` decorator to `POST /api/auth/allegro/device-flow` in `app/api/auth.py`
- [x] 2.2 Add `@admin_required` decorator to `POST /api/auth/allegro/device-token` in `app/api/auth.py`
- [x] 2.3 Add `@limiter.limit("30 per minute")` to `/api/scanner/barcode-preview` in `app/api/scanner.py`
- [x] 2.4 Add `MAX_QUERY_LENGTH = 128` validation and control character sanitization to barcode preview handler
- [x] 2.5 Add pytest tests for admin-only Allegro endpoints and rate-limited barcode preview

## 3. Data Integrity: Barcode, Cache Keys & Migration

- [x] 3.1 Remove `barcode[:47] + "..."` truncation from `_record_scan_telemetry` in `app/api/scanner.py`
- [x] 3.2 Add `max_length=128` to barcode field in `ScanBarcodeSchema` (`app/api/schemas.py`)
- [x] 3.3 Normalize query params in `make_facets_cache_key()`: sort with `parse_qsl` + `sorted()` + `urlencode()` in `app/core/cache.py`
- [x] 3.4 Fix Alembic migration `e3f891ab45c2` keyset pagination: advance `last_id` only for actually-updated rows
- [x] 3.5 Remove `time.sleep(0.1)` from migration chunk loop in `e3f891ab45c2`
- [x] 3.6 Add pytest tests for cache key normalization (same params, different order → same key)

## 4. Infrastructure: Docker & Rclone

- [x] 4.1 Update `.dockerignore` to exclude `.env`, `.env.*`, `docker-compose.override.yml`, `*.pem`, `*.key`, `*.crt`, `.venv`, `node_modules`, `frontend`, `tests`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.gemini`, `.agent`, `.agents`
- [x] 4.2 Remove duplicate rclone `copyto` block from `save_image()` in `app/utils/llm_covers.py` (lines 119-127)
- [x] 4.3 Verify `optimize_and_save_image()` in `app/utils/images.py` handles rclone push correctly as single source of truth

## 5. Documentation Fixes

- [x] 5.1 Restore TSDoc block comments for `CardWrapper` and `InstanceSettings` components in `frontend/components/admin/instance-settings.tsx`
- [x] 5.2 Update `docs/CHANGELOG.md` header from `## [0.7.14] - TBD` to `## [0.7.14] - 2026-08-08`
- [x] 5.3 Audit and update `README.md` system architecture section to reference PostgreSQL 18 and Redis 8

## 6. UX: Button Density & Visual Feedback

- [x] 6.1 Refactor `InstanceSettings` to group setting fields per domain into single `CardWrapper` with one primary "Save Changes" CTA
- [x] 6.2 Style secondary integration actions (e.g., "Authorize Allegro") with `variant="outline"` in `instance-settings.tsx`
- [x] 6.3 Consolidate FRBR Editor entity row actions into Shadcn `DropdownMenu` overflow menu in `frbr-editor.tsx`
- [x] 6.4 Implement `isProcessing` overlay in `camera-capture.tsx` with backdrop-blur, spinner, and pulsing text

## 7. Test Stability

- [x] 7.1 Revert `ux_audit.spec.ts` wait states from `domcontentloaded` back to `networkidle`
- [x] 7.2 Add route interception in `ux_audit.spec.ts` for `**/*.jpg` returning mock image buffers
- [x] 7.3 Create `frontend/__tests__/components/admin/instance-settings-allegro.test.tsx` with Vitest/RTL tests for OAuth device flow state machine
- [x] 7.4 Run `make test-backend` and `make test-frontend` to verify all fixes pass
- [x] 7.5 Run `make lint` to verify no new lint warnings introduced
