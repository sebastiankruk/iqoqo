## Context

See proposal.md for motivation. The system currently executes `agy_daemon.py` using a raw Docker run command with broad mounts (`~/.gemini`), while the Next.js auth exchange route trusts any `X-Forwarded-Host` header.

## Goals / Non-Goals

**Goals:**
- Eliminate Open Redirect risk by forcing a fallback to a trusted environment variable.
- Encapsulate the myKG daemon in a strict Sandbox with zero access to the host's `.gemini` folder, the codebase, or `.env` files.
- Retain the daemon's autonomous processing capability (`--dangerously-skip-permissions`).

**Non-Goals:**
- Applying egress proxy network filters (accepted the risk of outbound POSTs because of the surgical mount limit).
- Modifying the stable-diffusion compose file.

## Decisions

**1. Anchor Next.js Redirect Base URL**
- **Rationale:** Nginx proxies can be bypassed or misconfigured. Using `process.env.NEXT_PUBLIC_FRONTEND_URL` establishes a hard-coded, trusted origin.
- **Alternatives:** Hardening Nginx proxy headers (brittle, requires infrastructure change).

**2. Dedicated AI Sandbox (`docker-compose.ai_sandbox.yml`)**
- **Rationale:** Creating a dedicated compose file allows for strict constraints (`read_only: true`, `cap_drop: ALL`, `tmpfs`) without polluting other development compose files.
- **Alternatives:** Adding the service to `docker-compose.local-ai.yml`, which currently holds Stable Diffusion. Rejected due to separation of concerns.

**3. Surgical Credential Mount instead of Environment Variables**
- **Rationale:** Gemini Pro authentication relies on an OAuth refresh token in `credentials.json`. Mounting the entire `~/.gemini` folder risks exposing other agent sessions. We mount only `credentials.json` as read-only.
- **Alternatives:** Dropping the `--dangerously-skip-permissions` flag. Rejected because it breaks autonomous daemon execution.

## Risks / Trade-offs

- **Risk:** Autonomous agent exfiltrates `credentials.json` via prompt injection.
- **Mitigation:** The agent has zero access to `.env` or project source code. The worst-case blast radius is strictly limited to the `credentials.json` file.
