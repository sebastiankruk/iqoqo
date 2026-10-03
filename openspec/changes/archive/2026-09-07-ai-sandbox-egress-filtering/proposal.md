## Why

The autonomous AI sandbox environment (`docker-compose.ai_sandbox.yml`) was introduced to run background extraction and reasoning daemons (`agy`) with least-privilege system controls (`user: 1000:1000`, `cap_drop: ALL`, `read_only: true`, ephemeral `tmpfs`). However, the container currently attaches to Docker's default bridge network with unrestricted outbound Internet access (`0.0.0.0/0`). If malicious or untrusted prompt data compromises the runtime, the mounted Google OAuth credentials and session data could be exfiltrated to arbitrary external hosts. Restricting outbound network traffic strictly to authorized Google/Gemini API endpoints closes this exfiltration channel and enforces network-level least privilege.

## What Changes

- Introduce egress network filtering for `mykg-agy-daemon` in `docker-compose.ai_sandbox.yml` using a dedicated restricted bridge network and an egress-filtering forward proxy or firewall policy.
- Restrict outbound HTTP/HTTPS connections strictly to Google Gemini and Google OAuth endpoints (`generativelanguage.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`).
- Block all other outbound public Internet egress (e.g., arbitrary external IPs, third-party webhooks, arbitrary cloud endpoints).
- Block RFC1918 private network lateral movement from the sandbox container (e.g., connecting directly to backend, database, Redis, or internal host services).
- Configure standard proxy environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) in `docker-compose.ai_sandbox.yml` pointing to the internal egress filter.
- Add automated Bats tests to verify sandbox network egress enforcement (prohibiting unauthorized outbound connections while allowing Gemini API endpoints).

## Capabilities

### New Capabilities

- `ai-sandbox-egress-filtering`: Outbound network egress filtering and Google/Gemini domain allowlisting for autonomous AI sandbox containers.

### Modified Capabilities
<!-- None: container-hardening covers production web/frontend/db services; sandbox egress is a new capability -->

## Impact

- **Compose Configuration**: `docker-compose.ai_sandbox.yml` updated with restricted egress network definition and egress filtering proxy/service.
- **Tooling & Scripts**: `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py` and `Makefile` (`mykg-update`, `mykg-index`) leverage the filtered egress network when running `docker compose`.
- **Testing**: `tests/bash/mykg_tooling.bats` updated with egress isolation assertion tests.
- **Security Posture**: Resolves High-severity exfiltration vulnerability in the AI sandbox runtime.
