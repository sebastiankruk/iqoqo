## Why

Users running several iqoqo servers cannot tell which one the UI is connected to, and batch-scan mode on `/scan` has no unmistakable ON/OFF indicator. Separately, a real `iqoprerest` preview run (backend healthy after 8s) ended with a `make status` report that is not clean:

- **Spurious error:** `OTel Collector Export  3 export failures in last 5m` is reported as `fail` (`scripts/iqoqo-status.sh`, grep of `Exporting failed|HTTP Status Code 401` over a fixed 5-minute window). The collector started before OpenObserve was ready (collector up 44s, web up 13s), so these are startup-race errors, not a live fault.
- **Early `/health` probe:** `iqoprerest` calls the health endpoint before the stack is ready and shows errors, then reports healthy.
- **Env noise:** `Missing 33 variable(s)` mixes legitimate code/compose defaults (`APP_PORT`, `BACKUP_*`, `S3_*`, `SCHEDULER_AUTOSTART`, `OTEL_*_HOST_PORT`, `RUM_*`, `FEDERATION_*`, `ALLOW_PROD_*`) with potentially real gaps (`DEPLOY_TOKEN`, `BASE_URL`, `FEDERATION_HEAD_MODE`). The cause is `.env.example` entries with a non-empty example value being treated as "required" when absent from the active env file, so the operator cannot tell which matter.
- **Misleading line:** `Recent 5xx errors  7 in last 15min` is shown as a pass with a checkmark.
- **Stale-looking data:** `Migration  version: v1_0_0_add_apple_id_to_users` and `Health endpoint ... version=preview` give no confirmation of the expected revision/version.

## What Changes

- **Connected-server footer:** Show the connected server host in the shared `Footer`.
- **Batch-scan indicator:** Add a prominent, accessible ON/OFF indicator on `/scan`.
- **`iqoprerest` clean state:** Wait for readiness (bounded retry against the health endpoint, and for the OTel collector/OpenObserve dependency) before probing or running `make status`; show no transient error output; exit non-zero only if the stack never becomes healthy.
- **`make status` OTel check:** Count only export failures after the collector's last start (or after a short grace window), so startup races are not reported as `fail`; keep `fail` for sustained failures.
- **`make status` env classification:** Split missing variables into (a) has a built-in default in code/compose (info, not warning), (b) optional/not configured (info), (c) genuinely required and absent (warning). Source of truth is an explicit classification file kept next to `.env.example`, and a test fails when a new `.env.example` key is unclassified. No variable names are dropped silently.
- **`make status` 5xx line:** Show `info`/`warn` wording consistent with the count and use the warn threshold already in the script.
- **Docs:** Add a short section explaining each status category.

## Capabilities

### New Capabilities

- `connected-server-and-scan-state-visibility`: Footer server identity, batch-scan ON/OFF indicator, and a clean, accurate status/preview-restart experience.

### Modified Capabilities

<!-- Tracked under the new capability for v1.0.3 -->

## Impact

- **Frontend:** `Footer` component, `/scan` page, `frontend/messages/{en,pl}.json`
- **Tooling:** `scripts/iqoqo-status.sh` (OTel export check near line 483, environment section near line 1178, 5xx check near line 770), `iqoprerest` script, env classification file
- **Tests:** Vitest for footer and indicator; BATS/pytest for status classification and OTel grace window
