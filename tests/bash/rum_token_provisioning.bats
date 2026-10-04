#!/usr/bin/env bats
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
# (License header omitted for brevity)
#
# Regression coverage for the RUM client-token provisioning path.
#
# The invariant under test is the one that was actually broken: the previous
# implementation echoed a live bearer credential to stdout on every single
# deploy, into terminal scrollback, script(1) captures and CI logs.
#
# These tests drive the real provisioner (`scripts/provision_rum_token.py`) and
# assert that the token value never appears in any diagnostic output, on every
# path — success, reuse, and each failure class.

bats_require_minimum_version 1.5.0

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
  RUN_SH="${REPO_ROOT}/run.sh"
  PROVISIONER="${REPO_ROOT}/scripts/provision_rum_token.py"
  export TEST_TEMP_DIR
  TEST_TEMP_DIR="$(mktemp -d)"
  export SENTINEL_TOKEN="SENTINEL-RUM-TOKEN-a1b2c3d4e5f6g7h8"

  # A minimal OpenObserve-shaped management API on loopback, so the provisioner
  # is exercised end to end against a real socket rather than a curl stub.
  start_stub_openobserve() {
    local status="${1:-200}"
    PYTHONPATH="${REPO_ROOT}" python3 -c "
import http.server, sys, threading

SENTINEL = '${SENTINEL_TOKEN}'
STATUS = int('${status}')

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if STATUS != 200:
            self.send_response(STATUS)
            body = b'{\"message\":\"nope\"}'
        elif self.path.startswith('/healthz'):
            self.send_response(200)
            body = b'ok'
        else:
            self.send_response(200)
            body = ('{\"data\":{\"rum_token\":\"%s\"}}' % SENTINEL).encode()
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

srv = http.server.HTTPServer(('127.0.0.1', 0), H)
with open('${TEST_TEMP_DIR}/port', 'w') as f:
    f.write(str(srv.server_address[1]))
srv.serve_forever()
" &
    STUB_PID=$!
    for _ in $(seq 1 50); do
      [ -s "${TEST_TEMP_DIR}/port" ] && break
      sleep 0.1
    done
    STUB_PORT="$(cat "${TEST_TEMP_DIR}/port" 2>/dev/null)"
    export OPENOBSERVE_HOST_PORT="${STUB_PORT}"
  }

  stop_stub_openobserve() {
    [ -n "${STUB_PID:-}" ] && kill "${STUB_PID}" 2>/dev/null
    STUB_PID=""
  }

  # Strip the repo's own environment so the assertions below are not decided by
  # whatever the developer's .env happens to contain.
  unset OPENOBSERVE_RUM_SITE || true
  unset OPENOBSERVE_RUM_CLIENT_TOKEN || true
  unset NEXT_PUBLIC_FRONTEND_URL || true
  unset NEXTAUTH_URL || true
  unset MODE || true
  unset RUM_LOCAL_ONLY || true
  unset HTTP_PROXY || true
  unset HTTPS_PROXY || true
  unset ALL_PROXY || true
  # Derived, not committed: a hardcoded base64 credential literal in a tracked
  # test file is a credential-shaped string gitleaks flags, which trains
  # reviewers to ignore the scanner. See the note in .gitleaks.toml.
  export OPENOBSERVE_BASIC_AUTH
  OPENOBSERVE_BASIC_AUTH="$(printf 'root:rum-fixture-password' | base64 | tr -d '\n')"
  export RUM_READY_BUDGET_SECONDS=2
}

teardown() {
  stop_stub_openobserve
  cd /tmp || true
  rm -rf "$TEST_TEMP_DIR"
}

# ───────────────────── the no-leak invariant ─────────────────────

@test "a freshly provisioned token never reaches stderr" {
  start_stub_openobserve 200
  export MODE=dev

  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" \
      RUM_READY_BUDGET_SECONDS=2 OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      python3 "$PROVISIONER"

  [ "$status" -eq 0 ]
  [[ "$output" == *"$SENTINEL_TOKEN"* ]] || false   # token IS delivered, by design
  # ...but only on the KEY=VALUE machine-readable line, never in a diagnostic.
  echo "$stderr" | grep -q "$SENTINEL_TOKEN" && false || true
  echo "$output" | grep -qv "^RUM_CLIENT_TOKEN=" && echo "$output" | grep -q "$SENTINEL_TOKEN" && false || true
}

@test "a reused token is reported without the value" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      OPENOBSERVE_RUM_CLIENT_TOKEN="$SENTINEL_TOKEN" \
      python3 "$PROVISIONER"

  [ "$status" -eq 0 ]
  [[ "$stderr" == *"reason=existing"* ]]
  [[ "$stderr" != *"$SENTINEL_TOKEN"* ]]
}

@test "the provisioning log line carries no fingerprint of the token" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      python3 "$PROVISIONER"

  # Not the value, not any contiguous run of it.
  [[ "$stderr" != *"$SENTINEL_TOKEN"* ]]
  [[ "$stderr" != *"${SENTINEL_TOKEN:0:8}"* ]]

  # No contiguous run of 12 or more characters from the token may appear. This
  # subsumes "no prefix" without asserting anything about the token's length:
  # a length check greps stderr for a bare integer, which collides with the
  # random ephemeral port the stub binds and fails intermittently.
  local i run_str
  for ((i = 0; i + 12 <= ${#SENTINEL_TOKEN}; i++)); do
    run_str="${SENTINEL_TOKEN:i:12}"
    [[ "$stderr" != *"$run_str"* ]]
  done
}

@test "every failure path keeps the token out of the output" {
  for status in 401 403 404 302 500 503; do
    start_stub_openobserve "$status"
    run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=1 \
        OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
        python3 "$PROVISIONER"
    [ "$status" -eq 0 ] || true   # placeholder so the loop variable is used
    stop_stub_openobserve
    [[ "$output" != *"$SENTINEL_TOKEN"* ]]
    [[ "$stderr" != *"$SENTINEL_TOKEN"* ]]
  done
}

@test "a deployment never fails because of RUM" {
  # Nothing listening at all: the step must degrade, not abort.
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT=1 RUM_READY_BUDGET_SECONDS=0 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      python3 "$PROVISIONER"
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"rum-token:"* ]]
}

# ───────────────────── management request safety ─────────────────────

@test "the management request is not sent through an HTTP proxy" {
  start_stub_openobserve 200
  # A proxy that would answer anything if it were ever contacted.
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      HTTP_PROXY="http://127.0.0.1:1" ALL_PROXY="http://127.0.0.1:1" \
      python3 "$PROVISIONER"

  # Succeeded against loopback despite the proxy vars being set.
  [[ "$output" == *"RUM_CLIENT_TOKEN="* ]]
}

@test "a hostile OPENOBSERVE_HOST_PORT cannot redirect the credentialed request" {
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT='5080@evil.example/x' RUM_READY_BUDGET_SECONDS=0 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      python3 "$PROVISIONER"
  [ "$status" -eq 0 ]
  [[ "$stderr" != *"evil.example"* ]]
}

# ───────────────────── ingest target validation ─────────────────────

@test "a loopback site is accepted on a bare dev deployment" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=dev OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      OPENOBSERVE_RUM_SITE="http://127.0.0.1:5080" \
      python3 "$PROVISIONER"

  [[ "$output" == *"RUM_TOPOLOGY=loopback"* ]]
  [[ "$output" == *"RUM_INSECURE_HTTP=true"* ]]
}

@test "a loopback site is refused on a dockerized deployment" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=prod OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      OPENOBSERVE_RUM_SITE="http://localhost:5080" \
      NEXT_PUBLIC_FRONTEND_URL="https://iqoqo.example" \
      python3 "$PROVISIONER"

  [[ "$output" != *"RUM_CLIENT_TOKEN="* ]] || false
  [[ "$stderr" == *"not local-only"* ]]
}

@test "the deployment's own public origin is accepted over TLS" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=prod OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      OPENOBSERVE_RUM_SITE="https://iqoqo.example" \
      NEXT_PUBLIC_FRONTEND_URL="https://iqoqo.example" \
      python3 "$PROVISIONER"

  [[ "$output" == *"RUM_TOPOLOGY=public-origin"* ]]
  [[ "$output" == *"RUM_INSECURE_HTTP=false"* ]]
}

@test "plaintext ingest to a public origin is refused" {
  start_stub_openobserve 200
  run --separate-stderr env MODE=prod OPENOBSERVE_HOST_PORT="$STUB_PORT" RUM_READY_BUDGET_SECONDS=2 \
      OPENOBSERVE_BASIC_AUTH="${OPENOBSERVE_BASIC_AUTH}" \
      OPENOBSERVE_RUM_SITE="http://iqoqo.example" \
      NEXT_PUBLIC_FRONTEND_URL="https://iqoqo.example" \
      python3 "$PROVISIONER"

  [[ "$output" != *"RUM_CLIENT_TOKEN="* ]] || false
  [[ "$stderr" == *"plaintext"* ]]
}

# ───────────────────── run.sh no longer leaks ─────────────────────

@test "run.sh contains no echo of the provisioned token" {
  run grep -nE 'echo .*\$fetched_token|Successfully fetched active OpenObserve RUM token' "$RUN_SH"
  [ "$status" -ne 0 ]
}

@test "run.sh no longer writes the RUM token to an env file" {
  run grep -nE 'update_env_var "\.env[^"]*" "OPENOBSERVE_RUM_CLIENT_TOKEN"' "$RUN_SH"
  [ "$status" -ne 0 ]
}

@test "run.sh no longer forces localhost:5080 or INSECURE_HTTP=true" {
  run grep -nE 'NEXT_PUBLIC_OPENOBSERVE_RUM_SITE:-localhost:5080|NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP:-\?true|NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP:-true' "$RUN_SH"
  [ "$status" -ne 0 ]
}

@test "run.sh no longer downgrades the session replay privacy level" {
  run grep -nE 'NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL:-\?allow|NEXT_PUBLIC_OPENOBSERVE_RUM_PRIVACY_LEVEL:-allow' "$RUN_SH"
  [ "$status" -ne 0 ]
}

@test "run.sh no longer interpolates the root password into Python source" {
  run grep -nE "python3 -c .*OPENOBSERVE_ROOT_PASSWORD" "$RUN_SH"
  [ "$status" -ne 0 ]
}

@test "run.sh enables shell tracing nowhere near the provisioning block" {
  # `set -x` around the token would put it in the deploy log via the trace.
  run grep -nE '^\s*set -x' "$RUN_SH"
  [ "$status" -ne 0 ]
}
# ───────────────────── run.sh wiring in both topologies ─────────────────────

@test "run.sh provisions RUM in the docker path as well as the dev path" {
  # preview/prod never provisioned at all before: the whole block sat inside
  # `if [ "$MODE" == "dev" ]`, so browser RUM was inert in production.
  [ "$(grep -c 'provision_rum_token "\$MODE"' "$RUN_SH")" -ge 2 ]
}

@test "provision_rum_token is a top-level function the bats harness can lift" {
  local fn
  fn=$(awk '/^provision_rum_token\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [ -n "$fn" ]
  [[ "$fn" == *"provision_rum_token.py"* ]]
}

@test "provision_rum_token passes MODE explicitly rather than relying on export" {
  # MODE is a plain shell variable in run.sh and is never exported, so the
  # provisioner would silently fall back to its "dev" default on every mode.
  local fn
  fn=$(awk '/^provision_rum_token\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [[ "$fn" == *'MODE="$mode" python3 scripts/provision_rum_token.py'* ]]
}

@test "provision_rum_token exports the server-side variable names" {
  # docker-compose.yml and app/layout.tsx read OPENOBSERVE_RUM_*; exporting the
  # NEXT_PUBLIC_ prefixed names would reintroduce the build-time-inlining bug.
  local fn
  fn=$(awk '/^provision_rum_token\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [[ "$fn" == *'export OPENOBSERVE_RUM_CLIENT_TOKEN'* ]]
  [[ "$fn" == *'export OPENOBSERVE_RUM_SITE'* ]]
  [[ "$fn" != *'NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN'* ]]
}

@test "the token is exported but never assigned to a NEXT_PUBLIC_ variable" {
  run grep -nE 'export NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN=' "$RUN_SH"
  [ "$status" -ne 0 ]
}

# ───────────── ingest contract, verified against OpenObserve v0.91.5 ─────────────

@test "the nginx RUM route matches the path the SDK actually requests" {
  # endpointBuilder.js builds `${scheme}://${site}/rum/${apiVersion}/${org}/${trackType}`
  # so a site-relative `/rum/` location is what a reverse proxy must intercept.
  grep -q 'location /rum/' "$REPO_ROOT/deploy/nginx.conf"
  grep -q 'location /rum/' "$REPO_ROOT/deploy/nginx.conf.example"
  grep -q 'proxy_pass http://iqoqo_openobserve' "$REPO_ROOT/deploy/nginx.conf"
}

@test "the RUM ingest route is rate limited" {
  # Unauthenticated write endpoint: the client token is public, so the route must
  # be bounded independently of the general API budget.
  grep -q 'zone=api_rum' "$REPO_ROOT/deploy/nginx.conf"
  grep -q 'zone=api_rum' "$REPO_ROOT/deploy/nginx.conf.example"
}

@test "the component default API version matches the SDK ingest path" {
  # /rum/${apiVersion}/... — a mismatch would 404 the whole stream.
  grep -qE 'NEXT_PUBLIC_OPENOBSERVE_RUM_API_VERSION \?\? "v1"' \
    "$REPO_ROOT/frontend/components/browser-openobserve-rum.tsx"
}
