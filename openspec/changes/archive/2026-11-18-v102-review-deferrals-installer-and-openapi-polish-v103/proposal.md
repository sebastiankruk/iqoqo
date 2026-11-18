## Why

The `v1.0.2` Principal + Gemini Argon release audit (`.context/notes/review/1.0.2/principal-full-release-1.0.2-review.md`) cataloged 5 Low-priority (`🟢`) polish items (`L-01`–`L-05`) that do not block `v1.0.2` merge and are scheduled for `v1.0.3` (`C117`).

## What Changes

- **Bootstrap Installer Fallback Cleanup (`L-01` — `scripts/install.sh`):** Remove the temporary working branch `"feat/c110-store-submission-lts-audit-v102"` from `FALLBACK_BRANCHES` in `scripts/install.sh` (line 89), leaving only canonical release/main branches.
- **CI Optional Store Signing & Installer Checksum Packaging (`L-02` — `.github/workflows/mobile-build.yml`, `.github/workflows/ci.yml`):** Add conditional `if: ${{ secrets.ANDROID_KEYSTORE_BASE64 != '' }}` / `if: ${{ secrets.APPLE_CERTIFICATE_P12 != '' }}` release signing steps to `.github/workflows/mobile-build.yml` (`C110` task `1.2`) and package `scripts/iqoqo_installer.py` with a `sha256sum` checksum artifact in GitHub Actions (`C114` task `1.3`).
- **`iqopresync` Endpoint Probes & `DATABASE_URL` Password Encoding (`L-03` — `scripts/iqoqo_installer.py`):** URL-encode `POSTGRES_PASSWORD` via `urllib.parse.quote(pg_pass, safe="")` when constructing `DATABASE_URL` in `configure_env_content()`, and extend `run_presync_check()` to probe `/api/system/status` and `/.well-known/webfinger` alongside `/api/health` and `/.well-known/nodeinfo`.
- **OpenAPI 3.1 Query Parameter Schema for Ownership Items (`L-04` — `app/api/docs.py`):** Document `q`, `collection_status`, `format`, and `item_id` query parameters on `GET /api/v1/admin/ownership/items` in `app/api/docs.py`.
- **Changelog Setting Name, Unused Banner i18n Cleanup & Offline `collectionFilters` Predicate (`L-05` — `docs/CHANGELOG.md`, `frontend/messages/{en,pl}.json`, `frontend/app/collection/page.tsx`):** Replace `FEDERATION_READ_ONLY_HEAD` with `FEDERATION_HEAD_MODE` in `docs/CHANGELOG.md` line 16, remove unused `Navbar.federationHubBanner` / `Navbar.federationHubExploreDirectory` / `Navbar.dismissBanner` keys from `en.json` and `pl.json`, and evaluate `collectionFilters` inside the offline filtering predicate in `frontend/app/collection/page.tsx`.

## Capabilities

### New Capabilities
- `v102-review-deferrals-and-polish`: Resolves `v1.0.2` Low-severity review deferrals (`L-01`–`L-05`) across `scripts/install.sh`, `scripts/iqoqo_installer.py`, `.github/workflows/mobile-build.yml`, `app/api/docs.py`, `docs/CHANGELOG.md`, and `frontend/app/collection/page.tsx` in `v1.0.3`.

### Modified Capabilities
<!-- Tracked under the new v102-review-deferrals-and-polish capability for v1.0.3 -->

## Impact

- **Scripts & CI:** `scripts/install.sh`, `scripts/iqoqo_installer.py`, `.github/workflows/mobile-build.yml`
- **Backend OpenAPI:** `app/api/docs.py`
- **Frontend & Docs:** `frontend/app/collection/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`, `docs/CHANGELOG.md`
- **Tests:** `tests/scripts/test_iqoqo_installer.py`, `tests/test_infra_config.py`, `tests/test_openapi_contract_completeness.py`
