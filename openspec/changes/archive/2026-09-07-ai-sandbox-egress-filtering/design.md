## Context

The AI sandbox daemon (`mykg-agy-daemon`) runs in `docker-compose.ai_sandbox.yml` with strict local privileges (`user: 1000:1000`, `cap_drop: ALL`, `read_only: true`, ephemeral `tmpfs`). However, by default Docker Compose connects containers to an unrestricted bridge network. Because `cap_drop: ALL` is enforced, the daemon cannot manipulate host or container network filtering tables (`NET_ADMIN`).

To enforce least-privilege networking without compromising host configuration or requiring elevated container privileges, network isolation must be established at the Docker network topology level.

## Goals / Non-Goals

**Goals:**

- Enforce strict egress isolation: Prevent `mykg-agy-daemon` from establishing direct connections to arbitrary public Internet endpoints or private RFC1918 LAN services.
- Provide a dedicated egress proxy sidecar container in `docker-compose.ai_sandbox.yml` running on an isolated Docker network (`internal: true`).
- Restrict proxy CONNECT tunnels exclusively to verified Google/Gemini hostnames on port 443 (`generativelanguage.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`, `*.googleapis.com`).
- Maintain zero-privilege security posture (`no-new-privileges`, `cap_drop: ALL`, unprivileged user).
- Provide automated regression tests in `tests/bash/mykg_tooling.bats`.

**Non-Goals:**

- Deep TLS inspection/MITM: We do not decrypt or re-sign TLS payloads; CONNECT-level domain/SNI filtering at the proxy layer is sufficient to prevent exfiltration while preserving end-to-end TLS integrity.
- General production service egress filtering (PostgreSQL, Redis, web, frontend already operate on standard isolated internal networks).

## Decisions

### 1. Dual-Network Isolation with `internal: true`

- **Choice**: Place `mykg-agy-daemon` on a dedicated network (`sandbox-internal`) configured with `internal: true`.
- **Rationale**: Docker bridge networks with `internal: true` disable default gateway routing entirely. Even if the daemon tries to bypass proxy settings, it has no route to the Internet or external host networks.
- **Alternative Considered**: Host-level iptables / nftables. Rejected because host network setup is environment-dependent (Linux, Colima, Docker Desktop) and violates container portability.

### 2. Sidecar Egress Filtering Proxy

- **Choice**: Add an egress proxy service (`sandbox-egress-proxy`) in `docker-compose.ai_sandbox.yml` attached to both `sandbox-internal` and the default outbound bridge.
- **Rationale**: Acts as the sole gatekeeper. Configured with a strict domain allowlist:
  - `generativelanguage.googleapis.com`
  - `oauth2.googleapis.com`
  - `accounts.google.com`
  - `googleapis.com`
- **Alternative Considered**: DNS-only filtering (e.g. Pi-hole/CoreDNS sidecar). Rejected because malicious software can connect directly via IP addresses, bypassing DNS.

### 3. Proxy Configuration via Standard Environment Variables

- **Choice**: Inject `HTTP_PROXY=http://sandbox-egress-proxy:3128`, `HTTPS_PROXY=http://sandbox-egress-proxy:3128`, `NO_PROXY=localhost,127.0.0.1` into `mykg-agy-daemon`.
- **Rationale**: Respected out-of-the-box by standard CLI tools, Go/Rust binaries (like `agy`), and Python HTTP libraries (`urllib`, `requests`, `httpx`).

## Risks / Trade-offs

- **[Risk] Gemini API introduces a new required domain** → Mitigation: Use wildcard `*.googleapis.com` and maintain documented domain allowlist in proxy configuration.
- **[Risk] Proxy service failure prevents daemon operation** → Mitigation: Compose healthcheck on proxy service ensures `mykg-agy-daemon` only starts once egress proxy is healthy and responding.
- **[Risk] Resource overhead of extra container** → Mitigation: Use ultra-minimal proxy image (Tinyproxy or Alpine-based Squid) with strict memory limits (64M) and 0.1 CPU limit.

## Migration Plan

1. Update `docker-compose.ai_sandbox.yml` to define the proxy service, proxy configuration, and isolated network.
2. Update `Makefile` targets (`mykg-update`, `mykg-index`) to bring up both services during execution.
3. Update `tests/bash/mykg_tooling.bats` to validate network definitions, proxy environment variables, and egress allowlisting.
