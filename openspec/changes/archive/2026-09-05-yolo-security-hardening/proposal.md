## Why

A recent security audit identified critical vulnerabilities in the `v0.7.17` release, specifically concerning an Open Redirect via `X-Forwarded-Host` and dangerous credential exposure during autonomous myKG daemon execution (YOLO mode). These vulnerabilities could allow an attacker to spoof authentication redirects or exfiltrate Gemini Pro OAuth credentials via prompt injection. This change implements strict sandbox isolation and header validation to neutralize these threats.

## What Changes

- Fix the `frontend/app/api/auth-exchange/route.ts` to strictly fallback to the `NEXT_PUBLIC_FRONTEND_URL` environment variable, ignoring spoofed `X-Forwarded-Host` headers.
- Create a dedicated Docker Compose file (`docker-compose.ai_sandbox.yml`) to isolate the `mykg-agy-daemon` with dropped capabilities, a read-only root filesystem, strict resource limits, and an ephemeral `tmpfs` brain dump storage.
- Replace the blanket `~/.gemini` mount in the Makefile with a surgical, read-only mount of exactly `credentials.json`.
- Update the default myKG model from `gemini-3.7-flash-low` to `gemini-3.8-flash-low` in both the Makefile and `agy_daemon.py`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- **Affected Code**: `frontend/app/api/auth-exchange/route.ts`, `Makefile`, `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py`, `docker-compose.ai_sandbox.yml` (new).
- **Security Posture**: Massively improved isolation for the myKG daemon. Prompt injections can no longer exfiltrate host credentials or modify the codebase.
- **Dependencies**: No new external dependencies. Relies on Docker engine isolation features.
