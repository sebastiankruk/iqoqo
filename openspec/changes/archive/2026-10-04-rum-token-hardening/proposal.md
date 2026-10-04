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
- **Stop persisting the token at all.** Delete the env-file writes. `/api/default/rumtoken` is a server-side get-or-create, so the write buys nothing on re-run — and `update_env_var` appends with no shell escaping, so a value from an HTTP response body lands in a file that is `source`d under `allexport` on the next run. The tracked-file guard moves into `update_env_var` itself, where it protects `SECRET_KEY` rather than the public RUM token.
- **Fix the env file permissions that matter.** `.env` is mode `0664` and holds `SECRET_KEY`, `JWT_SECRET_KEY`, `AUTH_SECRET`, `OPENOBSERVE_ROOT_PASSWORD` and `OPENOBSERVE_BASIC_AUTH`, all world-readable to any local user. Tightening permissions only after the RUM token write would secure the one credential that is public by construction and leave the rest exposed.
- **Add explicit failure branches.** A `401`/`403` (rotated or wrong root password) is the most likely real-world cause and currently produces the same quiet warning as a missing route. It gets its own message naming the credential. A `3xx` must be treated as failure and **must not** be followed, because a redirected credentialed request can leak the root Basic auth off-box.
- **Pin the management endpoint to loopback.** Build the base URL from a loopback **literal** and the same host port used to bind the container, so there is no name to resolve and therefore no check-then-use window. Do not accept a fully-qualified URL from the environment, because `.env` is `source`d with `allexport` and a value there becomes the host that receives the root Basic credential.
- **Move the provisioning step into Python.** The bash implementation builds its Basic header by interpolating the root password into Python source — an argv exposure *and* an injection surface where a quote in the password silently degrades into an unauthenticated request. `http.client` reads credentials from `os.environ`, has no proxy support at all, and never follows redirects, so three of these requirements hold by construction rather than by flag.
- **Hand the browser the token at request time, and keep RUM working in both topologies.** The `NEXT_PUBLIC_*` value is compiled into the client bundle at build time, but `--prebuilt` prod pulls the frontend image from GHCR — so a per-instance build ARG would either be impossible or would bake one instance's token into a shared image. The server-side layout reads a non-public variable per request instead. Both shipping topologies then work: bare `dev` over HTTP on loopback, and dockerized `preview`/`prod` over HTTPS through a new `/rum/` reverse-proxy route with a corrected CORS origin list.
- **Log when the step does not run at all.** The whole block is gated on `OTEL_TRACES_EXPORTER=otlp` (`run.sh:536`). With tracing off, provisioning silently never happens. That case must warn too.
- **Treat a decryption failure as unset.** `decrypt_setting_value` returns the raw stored envelope on `InvalidToken` (`app/db/settings.py:167-169`). After a `SECRET_KEY` rotation, `get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")` therefore returns a dict, not a string. Consumers must validate the shape and treat a mismatch as unset, or the ciphertext envelope gets shipped to the browser as if it were a token.
- **Record the accepted risk in documentation.** `docs/MONITORING.md` must state that the RUM client token grants unauthenticated write access to the RUM stream, and record the retention and access posture of that stream — including that **no retention is configured**, which makes the token a disk-exhaustion primitive against the host volume, not merely a spam vector.
- **Correct the documented variable names.** `docs/MONITORING.md` documents `NEXT_PUBLIC_OPENOBSERVE_RUM_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_API_URL`, neither of which is read by the code. The code reads `NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_RUM_SITE`.

### Explicitly NOT changing

- The `/api/default/rumtoken` get-or-create contract. It is a single idempotent server-side call, which is strictly better than a list-then-create flow, and it is the mechanism that already works.
- `ensure_env_secrets.py`. The pre-boot pass is correct as-is: a RUM token cannot exist at line 313 because OpenObserve is not running yet.
- The `InstanceSettings` encryption scheme. `is_sensitive_key` already matches `_TOKEN`, so `OPENOBSERVE_RUM_CLIENT_TOKEN` is **already** encrypted at rest; only the shape-validation on read is missing.
- The loopback bind on OpenObserve (`docker-compose.monitoring.yml:31`). It is not part of this credential change, but it is the only control preventing an unauthenticated fill of the `openobserve_data` host volume, so it is recorded as load-bearing in the docs. Configuring retention is a required follow-up before any long-lived or disk-constrained deployment.

## Capabilities

### New Capabilities
- `observability/rum-token-hardening`: Security requirements for the existing deployment-time RUM client token path — no value in logs or files, a validated browser ingest target per deployment topology, request-time token delivery, a loopback-pinned management endpoint with no redirect or proxy path, distinct diagnostics per failure class, and correct handling of a `SECRET_KEY`-rotation decryption failure.

### Modified Capabilities
- `observability-health-validation`: this capability already requires `docs/MONITORING.md` to "accurately describe all 8 instrumented layers, default port topologies, **RUM token workflow**, ad-blocker resilience". This change rewrites exactly that text, so it carries a `MODIFIED` delta rather than silently editing a requirement that belongs to another capability.

## Impact

- **New file:** `scripts/provision_rum_token.py` replaces the inline bash implementation, plus `tests/bash/rum_token_provisioning.bats` and pytest coverage for its validation matrix.
- **Deployment flow:** `run.sh:547-575` becomes a call to the new script. `run.sh:711-714` stops forcing `RUM_SITE`, `RUM_INSECURE_HTTP` and `RUM_PRIVACY_LEVEL`.
- **Frontend:** `browser-openobserve-rum.tsx` becomes prop-driven; `app/layout.tsx` reads the token server-side per request; `insecureHTTP` defaults to `window.location.protocol === "http:"`.
- **Deploy topology:** `deploy/nginx.conf` gains a `/rum/` route; `docker-compose.yml` passes the token to the frontend service; `docker-compose.monitoring.yml` corrects `ZO_CORS_ALLOWED_ORIGINS`.
- **Settings:** `app/db/settings.py` read path — treat a decryption failure as unset, honour the caller's default, log the failure by key name only. No schema or encryption change.
- **Permissions:** `.env` and `.env.*` tightened to `0600`.
- **Docs:** `docs/MONITORING.md` gains the accepted-risk statement, the verified endpoint contract with its OpenObserve version, and corrected variable names; the non-existent `make monitoring-start`/`monitoring-stop` targets and the wrong `/api/health` path are corrected at the same time.
- **No verification spike is needed.** The endpoint (`/api/default/rumtoken`), auth method (root Basic), and response field (`data.rum_token`) are all already confirmed by the working call site in `run.sh:560-562`; a spike would have been pointed at a question the shipping code had already answered.
