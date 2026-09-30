## 1. Proxy Configuration & Sandbox Network Hardening

- [x] 1.1 Create proxy configuration file (Tinyproxy or Alpine-based Squid filter) allowlisting only `*.googleapis.com` and `accounts.google.com` on port 443 with default deny, and verify configuration parses cleanly
- [x] 1.2 Update `docker-compose.ai_sandbox.yml` with `sandbox-internal` network (`internal: true`), add `sandbox-egress-proxy` service, and configure proxy environment variables on `mykg-agy-daemon`, verifying with `docker compose -f docker-compose.ai_sandbox.yml config`

## 2. Tooling & Lifecycle Management

- [x] 2.1 Update `Makefile` `mykg-update` and `mykg-index` targets to ensure proxy lifecycle is managed alongside `mykg-agy-daemon`, verifying with `make -n mykg-update`

## 3. Test Coverage & Verification

- [x] 3.1 Add regression tests in `tests/bash/mykg_tooling.bats` verifying internal network definition, proxy environment variable binding, and egress restriction policy, validating with `bats tests/bash/mykg_tooling.bats`
- [x] 3.2 Run `IQOQO_AI_MODE=1 make lint` and ensure full test suite passes without warnings
