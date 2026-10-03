## Context

PR #208 introduces significant security, infrastructure, and UX changes for `release/0.7.14`. Eight specialized team reviewers plus GitHub Copilot identified 19 blocking issues across 7 capabilities. This design document covers how each will be remediated without altering the intended feature scope of the release.

## Goals / Non-Goals

**Goals:**

- Close all 12 CRITICAL and 7 IMPORTANT review findings before merging `release/0.7.14` to `main`
- Maintain backward compatibility with existing API contracts
- Ensure all fixes pass existing `make test-backend`, `make test-frontend`, and `make lint` suites

**Non-Goals:**

- Refactoring board game expansion ontology (deferred to v0.7.15)
- JSON-LD provenance mapping (deferred to v0.8.0)
- FRBR F3 column promotion (deferred to v0.8.0)
- Docker image size optimization (deferred to v0.8.0)

## Decisions

### D1: SSRF Redirect + DNS Rebinding Fix

- Set `allow_redirects=False` in `safe_get()` and implement a manual redirect loop capped at `max_redirects=5`
- On each redirect hop, re-resolve DNS and re-validate against `_BLOCKED_NETWORKS` via `is_ip_blocked()`
- For HTTPS: implement `SSRFProtectionAdapter` with `PinningHTTPSConnection` to pin socket-level IP while preserving SNI
- **Why not just TLS cert pinning alone?** TLS validates the *certificate* matches the hostname but doesn't prevent connecting to an internal IP if DNS rebinds between validation and connection

### D2: Duplicate Rclone Upload

- Remove the `rclone copyto` block from `save_image()` in `llm_covers.py`
- The rclone push responsibility belongs exclusively to `optimize_and_save_image()` in `images.py`

### D3: Barcode Truncation

- Replace `barcode[:47] + "..."` with Pydantic `max_length=128` validation on `ScanBarcodeSchema`
- Extend PostgreSQL column width for `scan_telemetry.barcode` to `VARCHAR(128)`

### D4: Cache Key Normalization

- Sort query parameters alphabetically in `make_facets_cache_key()` using `urllib.parse.parse_qsl` + `sorted()` + `urlencode()`

### D5: Migration Backfill Fix

- Replace `LIMIT/OFFSET` keyset with `WHERE id > :last_id ORDER BY id LIMIT :chunk_size` that advances `last_id` only when rows were actually updated
- Remove the `time.sleep(0.1)` that blocks container startup

### D6: UX Fixes

- **InstanceSettings**: Group settings per domain into single `CardWrapper` with one "Save Changes" CTA; style secondary actions with `variant="outline"`
- **FRBR Editor**: Move tertiary actions (Escalate, Delete) into Shadcn `DropdownMenu` 3-dot overflow; keep only Save + Add Child visible
- **Camera Viewfinder**: Add `isProcessing` state with backdrop-blur overlay, dual-ring spinner, and pulsing text

### D7: E2E Screenshot Stability

- Revert `waitForLoadState` from `domcontentloaded` back to `networkidle`
- Add route interception for `**/*.jpg` returning mock image buffers to prevent external network flakiness

## Risks / Trade-offs

- **Risk**: `SSRFProtectionAdapter` adds complexity to the HTTP client
  - **Mitigation**: Comprehensive `test_http_client.py` test suite already exists; extend with redirect-chain and DNS-rebinding tests
- **Risk**: Removing `time.sleep` from migration may increase DB load during backfill
  - **Mitigation**: Use `LIMIT 500` chunk size with explicit `COMMIT` per chunk for natural throttling
- **Risk**: UX changes (overflow menus, single-CTA) may surprise admin users
  - **Mitigation**: All actions remain accessible; only presentation hierarchy changes
