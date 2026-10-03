## Why

Deployment-time provisioning of the OpenObserve RUM client token **already exists** in `run.sh:547-575`: it waits for OpenObserve, authenticates with the root Basic credential, calls `GET /api/default/rumtoken`, and persists the result. An earlier draft of this change (**C18**, a number already taken by `moderate-findings-sweep`) proposed building that phase from scratch, on the mistaken premise that no provisioning path existed. That draft was wrong and has been discarded.

The real problem is that the existing implementation leaks and misroutes the credential it provisions:

- **`run.sh:564` prints the live bearer token to stdout on every single deploy** — into terminal scrollback, `script(1)` captures, and CI logs.
- **`run.sh:711-714` points the browser at `localhost:5080` with `INSECURE_HTTP=true`**, overriding the frontend's safer defaults of `window.location.host` and `insecureHTTP === false`. On any deployment that is not the operator's own machine, the end user's browser resolves `localhost` to *their own* computer and POSTs the freshly-provisioned token in cleartext to whatever is listening on their port 5080.
- **The token is written into tracked files and copied into backups.** `update_env_var` targets `.env` and `.env.dev`; `.env.test` is explicitly un-ignored in `.gitignore` and is a write target in `test` mode, and every `update_env_var` call also leaves a timestamped `.env.bak.<ts>` copy containing the token.

A RUM client token is a **public** credential by construction — it is a `NEXT_PUBLIC_*` value shipped in the browser bundle. Anyone can read it and write arbitrary RUM events, session replays, and log lines into the operator's OpenObserve. That threat is unstated anywhere in the repository today.

## What Changes

- **Stop emitting the token.** Remove the `echo` of the fetched token at `run.sh:564`. Provisioning must be observable by *outcome* ("RUM token provisioned", "RUM token unchanged") and never by value.
- **Validate the browser ingest target before handing over a credential.** The `site` passed to the browser must be an absolute URL whose host is a loopback address (dev) or the deployment's own public origin (prod). A `localhost`/relative target on a non-loopback deployment, or plaintext ingest to a non-loopback host, must leave RUM disabled with a distinct warning. The frontend's existing safe defaults must be allowed to stand rather than being overridden to something less safe.
- **Stop persisting the token into tracked files.** Refuse to write a live token to any path reported by `git ls-files`, and stop snapshotting env files that contain a live token.
- **Add explicit failure branches.** A `401`/`403` (rotated or wrong root password) is the most likely real-world cause and currently produces the same quiet warning as a missing route. It gets its own message naming the credential. A `3xx` must be treated as failure and **must not** be followed, because a redirected credentialed request can leak the root Basic auth off-box.
- **Pin the management endpoint to loopback.** Derive the base URL from the same `OPENOBSERVE_HOST_PORT` used to bind the container, resolve it, and refuse any target that does not resolve to loopback. Do not accept a fully-qualified URL from the environment, because `.env` is `source`d with `allexport` and a value there becomes the host that receives the root password.
- **Log when the step does not run at all.** The whole block is gated on `OTEL_TRACES_EXPORTER=otlp` (`run.sh:536`). With tracing off, provisioning silently never happens. That case must warn too.
- **Treat a decryption failure as unset.** `decrypt_setting_value` returns the raw stored envelope on `InvalidToken` (`app/db/settings.py:167-169`). After a `SECRET_KEY` rotation, `get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")` therefore returns a dict, not a string. Consumers must validate the shape and treat a mismatch as unset, or the ciphertext envelope gets shipped to the browser as if it were a token.
- **Record the accepted risk in documentation.** `docs/MONITORING.md` must state that the RUM client token grants unauthenticated write access to the RUM stream, and record the retention and access posture of that stream.
- **Correct the documented variable names.** `docs/MONITORING.md` documents `NEXT_PUBLIC_OPENOBSERVE_RUM_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_API_URL`, neither of which is read by the code. The code reads `NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_RUM_SITE`.

### Explicitly NOT changing

- The `/api/default/rumtoken` get-or-create contract. It is a single idempotent server-side call, which is strictly better than a list-then-create flow, and it is the mechanism that already works.
- `ensure_env_secrets.py`. The pre-boot pass is correct as-is: a RUM token cannot exist at line 313 because OpenObserve is not running yet.
- The `InstanceSettings` encryption scheme. `is_sensitive_key` already matches `_TOKEN`, so `OPENOBSERVE_RUM_CLIENT_TOKEN` is **already** encrypted at rest; only the shape-validation on read is missing.

## Capabilities

### New Capabilities
- `observability/rum-token-hardening`: Security requirements for the existing deployment-time RUM client token path — no value in logs, validated browser ingest target before a credential is handed to the browser, no persistence into tracked files, loopback-pinned management endpoint with no redirect following, distinct diagnostics per failure class, and correct handling of a `SECRET_KEY`-rotation decryption failure.

### Modified Capabilities

None. No existing spec-level requirement changes; this adds requirements to a path that already ships.

## Impact

- **Deployment flow:** `run.sh:547-575` and `run.sh:711-714`. The provisioning call itself is unchanged; what changes is what is printed, what is persisted, and what the browser is told to talk to.
- **Settings:** `app/db/settings.py` read-path shape validation. No schema or encryption change.
- **Frontend:** `frontend/components/browser-openobserve-rum.tsx` — the safe defaults it already has (`window.location.host`, `insecureHTTP === "true"` ⇒ false) stop being overridden by the deploy path.
- **Docs:** `docs/MONITORING.md` gains the accepted-risk statement and corrected variable names.
- **Testing:** bats coverage for the no-leak invariant (a sentinel token must never appear in captured output on any path), the ingest-target validation matrix, and the `401`/`403`/`3xx` branches.
- **No verification spike is needed.** The endpoint (`/api/default/rumtoken`), auth method (root Basic), and response field (`data.rum_token`) are all already confirmed by the working call site in `run.sh:560-562`; a spike would have been pointed at a question the shipping code had already answered.
