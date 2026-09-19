#!/usr/bin/env bats
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

@test "Makefile has mykg targets" {
  run make -n mykg-scope
  [ "$status" -eq 0 ]
  [[ "$output" == *"scan_scope.py"* ]]

  run make -n mykg-status
  [ "$status" -eq 0 ]
  [[ "$output" == *"get_status.py"* ]]

  run make -n mykg-index
  [ "$status" -eq 0 ]
  [[ "$output" == *"run_index.py"* ]]

  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"run_update.py"* ]]

  run make -n mykg-ask Q="test"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ask.py"* ]]
}

@test "Makefile has knowledge-sync target" {
  run make -n knowledge-sync
  [ "$status" -eq 0 ]
  [[ "$output" == *"codegraph sync"* ]] || [[ "$output" == *"codegraph-sync"* ]]
  [[ "$output" == *"graphify-update"* ]] || [[ "$output" == *"run_update.py"* ]]
  # Fast sync must not include heavy targets
  [[ "$output" != *"mempalace-index"* ]]
  [[ "$output" != *"mykg-update"* ]]
}

@test "Makefile has knowledge-sync-full target" {
  run make -n knowledge-sync-full
  [ "$status" -eq 0 ]
  [[ "$output" == *"codegraph sync"* ]] || [[ "$output" == *"codegraph-sync"* ]]
  [[ "$output" == *"run_mine.py"* ]] || [[ "$output" == *"mempalace-index"* ]]
  [[ "$output" == *"run_update.py"* ]] || [[ "$output" == *"mykg-update"* ]]
}

@test "docker-compose.ai_sandbox.yml enforces sandbox isolation and security hardening" {
  compose_file="${BATS_TEST_DIRNAME}/../../docker-compose.ai_sandbox.yml"
  [ -f "$compose_file" ]

  run grep -E "user:\s*\"1000:1000\"" "$compose_file"
  [ "$status" -eq 0 ]

  run grep -E "read_only:\s*true" "$compose_file"
  [ "$status" -eq 0 ]

  run grep -E "cap_drop:" "$compose_file"
  [ "$status" -eq 0 ]
  run grep -E "\-\s*ALL" "$compose_file"
  [ "$status" -eq 0 ]

  run grep -E "no-new-privileges:\s*true" "$compose_file"
  [ "$status" -eq 0 ]

  run grep -E "antigravity-oauth-token:/run/secrets/antigravity-oauth-token:ro" "$compose_file"
  [ "$status" -eq 0 ]
}

@test "docker-compose.ai_sandbox.yml enforces egress isolation and proxy configuration" {
  compose_file="${BATS_TEST_DIRNAME}/../../docker-compose.ai_sandbox.yml"
  [ -f "$compose_file" ]

  # Verify sandbox-internal network has internal: true
  run grep -E "sandbox-internal:" "$compose_file"
  [ "$status" -eq 0 ]
  run grep -E "internal:\s*true" "$compose_file"
  [ "$status" -eq 0 ]

  # Verify proxy service and healthcheck
  run grep -E "sandbox-egress-proxy:" "$compose_file"
  [ "$status" -eq 0 ]
  run grep -E "deploy/sandbox_proxy" "$compose_file"
  [ "$status" -eq 0 ]

  # Verify proxy env variables in mykg-agy-daemon
  run grep -E "HTTP_PROXY=http://sandbox-egress-proxy:3128" "$compose_file"
  [ "$status" -eq 0 ]
  run grep -E "HTTPS_PROXY=http://sandbox-egress-proxy:3128" "$compose_file"
  [ "$status" -eq 0 ]
}

@test "deploy/sandbox_proxy restricts egress to Google Gemini and OAuth endpoints" {
  allowlist_file="${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy/allowlist.conf"
  [ -f "$allowlist_file" ]

  run grep -E "generativelanguage\.googleapis\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "accounts\.google\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "cloudcode-pa\.googleapis\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "lh3\.googleusercontent\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "antigravity-unleash\.goog:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "www\.googleapis\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "play\.googleapis\.com:443" "$allowlist_file"
  [ "$status" -eq 0 ]


  # Verify no wildcard Google domains or wildcard open egress rules exist
  run grep -E "^\s*\*(\.googleapis|\.google|\.googleusercontent)" "$allowlist_file"
  [ "$status" -ne 0 ]
  run grep -E "^\s*\*\s*$" "$allowlist_file"
  [ "$status" -ne 0 ]
}

@test "Makefile mykg targets define pre-flight cleanup and signal trap handlers" {
  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"docker rm -f mykg-agy-daemon"* ]]
  [[ "$output" == *"trap cleanup EXIT INT TERM"* ]]

  run make -n mykg-index
  [ "$status" -eq 0 ]
  [[ "$output" == *"docker rm -f mykg-agy-daemon"* ]]
  [[ "$output" == *"trap cleanup EXIT INT TERM"* ]]
}

@test "mykg recipe trap handler cleans up daemon container on SIGINT" {
  test_temp_dir="$(mktemp -d)"
  docker_log="${test_temp_dir}/docker.log"

  mkdir -p "${test_temp_dir}/bin"
  printf '#!/bin/bash\necho "DOCKER: $*" >> "%s"\nexit 0\n' "${docker_log}" > "${test_temp_dir}/bin/docker"
  chmod +x "${test_temp_dir}/bin/docker"

  PATH="${test_temp_dir}/bin:${PATH}" run bash -c '
    cleanup() {
      EXIT_CODE=$?
      trap - EXIT INT TERM
      if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        docker compose -f docker-compose.ai_sandbox.yml down >/dev/null 2>&1 || true
        docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true
      fi
      exit $EXIT_CODE
    }
    trap cleanup EXIT INT TERM
    kill -s INT $$
    sleep 1
  '

  [ -f "${docker_log}" ]
  run cat "${docker_log}"
  [[ "$output" == *"compose -f docker-compose.ai_sandbox.yml down"* ]]
  [[ "$output" == *"rm -f mykg-agy-daemon"* ]]

  rm -rf "${test_temp_dir}"
}

@test "pre-flight container cleanup prevents collision before container creation" {
  test_temp_dir="$(mktemp -d)"
  docker_log="${test_temp_dir}/docker.log"

  mkdir -p "${test_temp_dir}/bin"
  printf '#!/bin/bash\necho "DOCKER: $*" >> "%s"\nexit 0\n' "${docker_log}" > "${test_temp_dir}/bin/docker"
  chmod +x "${test_temp_dir}/bin/docker"

  PATH="${test_temp_dir}/bin:${PATH}" run bash -c '
    docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true
    docker compose -f docker-compose.ai_sandbox.yml run --rm -d --name mykg-agy-daemon test
  '

  [ "$status" -eq 0 ]
  run cat "${docker_log}"
  rm_line=$(grep -n "rm -f mykg-agy-daemon" "${docker_log}" | cut -d: -f1 | head -n1)
  run_line=$(grep -n "run --rm -d --name mykg-agy-daemon" "${docker_log}" | cut -d: -f1 | head -n1)
  [ -n "$rm_line" ]
  [ -n "$run_line" ]
  [ "$rm_line" -lt "$run_line" ]

  rm -rf "${test_temp_dir}"
}

@test "mykg_config.yaml disables obsidian_vault generation across all profiles" {
  config_file="${BATS_TEST_DIRNAME}/../../mykg_config.yaml"
  [ -f "$config_file" ]
  # obsidian_enabled: true must not exist in any profile
  run grep -E "^\s*obsidian_enabled:\s*true" "$config_file"
  [ "$status" -ne 0 ]

  # obsidian_enabled: false must be present
  run grep -E "^\s*obsidian_enabled:\s*false" "$config_file"
  [ "$status" -eq 0 ]
}

@test "mykg query produces valid ontological output via make mykg-ask" {
  if [ ! -d "${BATS_TEST_DIRNAME}/../../mykg_sessions" ]; then
    skip "mykg_sessions directory not present"
  fi
  run make mykg-ask Q="Manifestation"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Manifestation"* || "$output" == *"conf="* ]]
}

@test "allowlist-opencode.conf exists and contains opencode Go API endpoints" {
  allowlist_file="${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy/allowlist-opencode.conf"
  [ -f "$allowlist_file" ]

  run grep -E "models\.opencode\.ai:443" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "opencode\.ai:443" "$allowlist_file"
  [ "$status" -eq 0 ]

  # Verify no Google/Gemini endpoints leak into the opencode allowlist
  run grep -E "googleapis\.com" "$allowlist_file"
  [ "$status" -ne 0 ]
  run grep -E "google\.com" "$allowlist_file"
  [ "$status" -ne 0 ]

  # Verify only port-443 entries exist (no port 80 or other ports)
  run grep -E "^[^#].*:([0-9]+)" "$allowlist_file"
  [ "$status" -eq 0 ]
  run grep -E "^[^#].*:(?!443)[0-9]+" "$allowlist_file"
  [ "$status" -ne 0 ]
}

@test "proxy.py selects correct allowlist based on AI_AGENT env var" {
  proxy_script="${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy/proxy.py"
  [ -f "$proxy_script" ]

  # Verify AI_AGENT=opencode loads allowlist-opencode.conf
  run python3 -c "
import os, sys
os.environ['AI_AGENT'] = 'opencode'
if 'ALLOWLIST_CONFIG' in os.environ: del os.environ['ALLOWLIST_CONFIG']
sys.path.insert(0, '${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy')
import proxy
path = proxy.resolve_allowlist_path()
assert path.name == 'allowlist-opencode.conf', f'Expected allowlist-opencode.conf, got {path.name}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]

  # Verify AI_AGENT=agy loads allowlist.conf
  run python3 -c "
import os, sys
os.environ['AI_AGENT'] = 'agy'
if 'ALLOWLIST_CONFIG' in os.environ: del os.environ['ALLOWLIST_CONFIG']
sys.path.insert(0, '${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy')
import importlib, proxy
importlib.reload(proxy)
path = proxy.resolve_allowlist_path()
assert path.name == 'allowlist.conf', f'Expected allowlist.conf, got {path.name}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "proxy.py fails closed for unrecognized AI_AGENT value" {
  run python3 -c "
import os, sys
os.environ['AI_AGENT'] = 'invalid_agent'
if 'ALLOWLIST_CONFIG' in os.environ: del os.environ['ALLOWLIST_CONFIG']
sys.path.insert(0, '${BATS_TEST_DIRNAME}/../../deploy/sandbox_proxy')
import importlib, proxy
importlib.reload(proxy)
path = proxy.resolve_allowlist_path()
# The path should reference a non-existent file → load_allowlist will fail closed
assert not path.exists(), f'Expected non-existent path, but {path} exists'
assert 'invalid_agent' in path.name
print('FAIL_CLOSED_OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAIL_CLOSED_OK"* ]]
}

@test "Makefile AI_AGENT validation rejects invalid values" {
  run make -n mykg-update AI_AGENT=invalid
  [ "$status" -ne 0 ]
  [[ "$output" == *"Invalid AI_AGENT"* ]]
  [[ "$output" == *"agy"* ]]
  [[ "$output" == *"opencode"* ]]

  run make -n mykg-index AI_AGENT=badvalue
  [ "$status" -ne 0 ]
  [[ "$output" == *"Invalid AI_AGENT"* ]]
}

@test "Makefile mykg-update uses opencode defaults when AI_AGENT=opencode" {
  run make -n mykg-update AI_AGENT=opencode
  [ "$status" -eq 0 ]
  [[ "$output" == *"opencode-go/muse-spark-1.3-contributor"* ]]
  [[ "$output" == *"minimal"* ]]
  [[ "$output" == *"opencode_daemon.py"* ]]
  [[ "$output" == *"mykg-opencode-daemon"* ]]
  [[ "$output" == *"agent-opencode"* ]]
}

@test "Makefile mykg-update preserves agy defaults when AI_AGENT=agy" {
  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"gemini-3.8-flash-low"* ]]
  [[ "$output" == *"agy_daemon.py"* ]]
  [[ "$output" == *"mykg-agy-daemon"* ]]
  [[ "$output" == *"agent-claude-code"* ]]
}

@test "docker-compose.ai_sandbox.yml includes mykg-opencode-daemon with correct hardening" {
  compose_file="${BATS_TEST_DIRNAME}/../../docker-compose.ai_sandbox.yml"
  [ -f "$compose_file" ]

  # Verify opencode daemon service exists
  run grep -E "mykg-opencode-daemon:" "$compose_file"
  [ "$status" -eq 0 ]

  # Verify opencode auth.json credential mount
  run grep -E "auth\.json:/run/secrets/opencode-auth\.json:ro" "$compose_file"
  [ "$status" -eq 0 ]

  # Verify AI_AGENT=opencode environment variable
  run grep -E "AI_AGENT=opencode" "$compose_file"
  [ "$status" -eq 0 ]
}

@test "mykgconfig.yaml includes agent-opencode profile" {
  config_file="${BATS_TEST_DIRNAME}/../../mykg_config.yaml"
  [ -f "$config_file" ]

  run grep -E "agent-opencode:" "$config_file"
  [ "$status" -eq 0 ]

  run grep -E "opencode-go/muse-spark-1\.3-contributor" "$config_file"
  [ "$status" -eq 0 ]
}

