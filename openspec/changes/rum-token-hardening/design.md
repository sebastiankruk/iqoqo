## Context

OpenObserve runs as a per-deployment local image, so its RUM client token is inherently per-instance and cannot be shipped in the repository. Today it is neither provisioned nor documented, and a hardcoded token previously sat in `.env.test`, `frontend/.env.example` and a `run.sh` fallback. Those have been removed, so RUM is currently disabled everywhere unless an operator sets a token through the OpenObserve UI by hand.

`scripts/ensure_env_secrets.py` already provisions the other three OpenObserve credentials locally, which is why this gap is conspicuous: the RUM token is the only credential in that family with no provisioning path.

There is no unknown API to discover. `run.sh:560-562` already calls `GET /api/default/rumtoken` with root Basic auth and reads `data.rum_token`, and that call works. The endpoint is also a server-side get-or-create, which is strictly better than a list-then-create flow and is retained unchanged. The work in this change is remediation of that existing path, not construction of a new one.

## Goals / Non-Goals

**Goals:**
- Provision a per-instance RUM client token at deployment time, so browser RUM works with no manual step and no committed credential.
- Keep the failure mode soft: RUM is optional telemetry and must never block, fail, or slow down a deployment.
- Keep the token a secret: restrictive file permissions, encrypted at rest in `InstanceSettings`, never logged, never committed.
- Leave an accurate manual path for deployments that disable automation.

**Non-Goals:**
- Provisioning OTLP ingest credentials, log-shipper tokens, or any other OpenObserve credential — those already have paths.
- Making RUM mandatory, or failing startup when RUM is unavailable.
- Exposing RUM data through the application or adding new telemetry signals.
- Reworking the existing `ensure_env_secrets.py` pre-boot pass, which is correct as-is for the credentials it handles.

## Decisions

### Decision 1: Two-phase provisioning, because OpenObserve does not exist at secret-provisioning time

The boot order in `run.sh` is load-bearing and was verified against the merged code:

| Line | Step |
|------|------|
| 313 | `auto_generate_or_rotate_keys` → `ensure_env_secrets.py` provisions local secrets |
| 487 / 526 | `docker compose up -d db redis` |
| 545 | `docker compose -f docker-compose.monitoring.yml up -d` → OpenObserve starts |
| 694 | Frontend (`npx next dev`) starts, consuming `NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN` |

A RUM client token is only meaningful once an application row exists inside OpenObserve, and that can only be created over its management API. At line 313 the container has not been created yet. So `ensure_env_secrets.py` is deliberately **not** extended — reaching OpenObserve from the pre-boot pass would add a dependency on a container that does not exist and would invert the startup order.

Instead the new step lives between lines 545 and 694: OpenObserve is running, and the frontend has not yet been launched. That window is the only place the operation is both possible and useful.

**Alternatives considered:**
- *Provision in the pre-boot pass anyway.* Rejected: OpenObserve is not listening, so the call cannot succeed, and adding a retry loop there would stall startup for the full timeout on every deployment.
- *Provision from a container entrypoint.* Rejected: the OpenObserve service has no knowledge of the host env file, and it would entangle an optional observability concern with the core API container's start-up.
- *Generate the token locally and pass it in.* Rejected: the token must correspond to a row in OpenObserve; a locally generated string is not a valid RUM client token and ingest would reject it.

### Decision 2: Fail-soft, and why that is a requirement rather than caution

RUM is one optional signal among logs, metrics and traces. Provisioning it must not be able to fail a deployment, and an OpenObserve upgrade that removes or reshapes the endpoint must degrade rather than break every instance. Therefore a missing route (404), a transient error, a timeout, and even a 2xx response with no token all end the same way: log once, leave RUM disabled, exit zero.

This is also what makes the unverified API surface acceptable to build against. If the spike finds no management API, the shipped behaviour is already the correct degraded state, and the automation is simply dropped rather than shipped as a permanent no-op.

### Decision 3: Idempotent create-or-fetch

Repeated `./run.sh preview` invocations must converge on one application and one token. Creating blindly would accumulate orphaned RUM applications on every restart, each of which is another ingest endpoint nobody is watching.

If the spike finds the client token is only returned at creation time and cannot be read back, this requirement has to change to "persist on first creation and reuse thereafter". That is a spec-level change and is called out explicitly in task 1.3 rather than discovered during implementation.

### Decision 4: Treat the token as a secret end to end

It is a bearer credential for log ingestion. It goes into the env file with the same restrictive permissions as the other provisioned secrets, into `InstanceSettings` encrypted at rest, and never into stdout, a log, or version control. The earlier committed token is the concrete argument: any token-shaped literal in a tracked file is indistinguishable from a leak to every future scanner and reviewer.

## Risks / Trade-offs

- **[Risk] The management API does not exist in v0.91.5.** Mitigated by making the verification spike task 1 and gating everything else on it. The fallback is the documentation-only path, which is already the shipped behaviour.
- **[Risk] The API exists but is not stable across OpenObserve versions.** Mitigated by fail-soft on 404 and by recording the verified contract *and the version it was verified against* in `docs/MONITORING.md`, so an upgrade has something concrete to re-check rather than a silent regression.
- **[Risk] RUM stays silently off and nobody notices.** Accepted. The step logs an actionable warning on every degradation path, which is the correct trade against failing deployments. The documentation task makes the manual path discoverable.
- **[Trade-off] A bounded health wait adds startup latency on the degraded path.** Accepted and bounded; it is the cost of not failing closed, and it only elapses when OpenObserve is actually absent.
- **[Trade-off] Writing the token to the host env file keeps it in plaintext on disk.** Accepted: it matches how the other OpenObserve credentials are handled, and the alternative (provisioning only into the database) would not reach the frontend build.

## Migration Plan

1. Run the verification spike and record the API contract. Stop if the route is absent.
2. Add `scripts/provision_rum_token.py` with full fail-soft handling and bats coverage.
3. Wire it into `run.sh` between the monitoring start and the frontend start.
4. Add the encrypted `InstanceSettings` key and confirm the frontend's unset-token path.
5. Document the manual fallback and the verified contract.
6. Verify on a real instance: RUM reaches OpenObserve after `./run.sh preview`, and the token survives a restart unchanged.

No migration is required for existing deployments: RUM is already disabled after the hardcoded token was removed, so this change can only turn a currently-absent feature on.
