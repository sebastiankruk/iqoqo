## Context

See `proposal.md` for the detailed root-cause analysis. `make status prod` currently emits a false warning for Allegro due to unauthenticated requests to a protected endpoint and running Flask model operations outside an active application context.

## Goals / Non-Goals

**Goals:**
- Fix `scripts/iqoqo-status.sh` to properly execute the Python probe inside a Flask application context (`app.app_context()`).
- Refine status discrimination in `scripts/iqoqo-status.sh` so probe execution errors (`reason: query_failed` or `probe_error`) are treated as diagnostic warnings about probe execution, not misleading OAuth handshake warnings.
- Ensure `get_allegro_token_status` in `app/utils/allegro.py` treats refreshable tokens as active while surfacing `needs_refresh` diagnostics cleanly.

**Non-Goals:**
- Changing the Allegro OAuth device code flow itself.
- Removing `@require_auth` from administrative endpoints without authorization checks.

## Decisions

- **Decision 1: App context initialization in inline probe.**
  - *Rationale:* Rather than exposing sensitive integration status publicly on an unauthenticated HTTP route, running the local CLI probe via `create_app().app_context()` preserves security boundaries while giving the status script direct access to `InstanceSettings`.
  - *Alternatives considered:* Making `/api/system/status` unauthenticated (rejected: exposes version and configuration details to anonymous visitors).
- **Decision 2: Clear failure categorization in `scripts/iqoqo-status.sh`.**
  - *Rationale:* If the container or database is down, report `probe error` with `warn` or `fail` instead of `OAuth handshake pending`.

## Risks / Trade-offs

- **[Risk]** Slightly slower execution for `header "Allegro API"` in `iqoqo-status.sh` due to `create_app()` startup.
  - *Mitigation:* `create_app()` executes in <200ms in modern Python/Flask environments and is only run once during the status check.
