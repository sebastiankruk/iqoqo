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

  # MOD-OPS-04: index/update now dispatch through scripts/mykg_sync.sh, which
  # selects run_index.py / run_update.py internally.
  run make -n mykg-index
  [ "$status" -eq 0 ]
  [[ "$output" == *"scripts/mykg_sync.sh index"* ]]

  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"scripts/mykg_sync.sh update"* ]]

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

@test "Makefile mykg targets delegate sandbox lifecycle to scripts/mykg_sync.sh" {
  # MOD-OPS-04: the ~45 lines of backslash-continued shell per target moved out
  # of the Makefile. The Makefile must now be a thin wrapper, not a second copy.
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"
  [ -f "$sync_script" ]

  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"scripts/mykg_sync.sh update"* ]]
  # The daemon wiring must no longer be duplicated inline in the recipe.
  [[ "$output" != *"docker rm -f mykg-agy-daemon"* ]]
  [[ "$output" != *"trap cleanup EXIT INT TERM"* ]]

  run make -n mykg-index
  [ "$status" -eq 0 ]
  [[ "$output" == *"scripts/mykg_sync.sh index"* ]]
  [[ "$output" != *"docker rm -f mykg-agy-daemon"* ]]
  [[ "$output" != *"trap cleanup EXIT INT TERM"* ]]
}

@test "Makefile forwards the AI agent, model, effort and profile to the sync script" {
  run make -n mykg-update AI_AGENT=opencode
  [ "$status" -eq 0 ]
  [[ "$output" == *'AI_AGENT="opencode"'* ]]
  [[ "$output" == *'MYKG_MODEL="opencode-go/longcat-2.5-preview-free"'* ]]
  [[ "$output" == *'MYKG_EFFORT="low"'* ]]
  [[ "$output" == *'MYKG_PROFILE="agent-opencode"'* ]]
}

@test "mykg_sync.sh defines pre-flight cleanup and signal trap handlers" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  run grep -F 'trap cleanup EXIT INT TERM' "$sync_script"
  [ "$status" -eq 0 ]

  # Pre-flight removal must precede creation so a leaked daemon from an
  # interrupted run cannot cause a --name collision.
  rm_line=$(grep -n 'docker rm -f "$AI_CONTAINER"' "$sync_script" | head -1 | cut -d: -f1)
  run_line=$(grep -n 'run --rm -d --name "$AI_CONTAINER"' "$sync_script" | head -1 | cut -d: -f1)
  [ -n "$rm_line" ]
  [ -n "$run_line" ]
  [ "$rm_line" -lt "$run_line" ]

  # Teardown must remove both daemons and bring the compose stack down.
  run grep -F 'docker compose -f "$COMPOSE_FILE" down' "$sync_script"
  [ "$status" -eq 0 ]
  run grep -F 'docker rm -f mykg-agy-daemon' "$sync_script"
  [ "$status" -eq 0 ]
  run grep -F 'docker rm -f mykg-opencode-daemon' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "mykg_sync.sh selects the daemon script and container per AI_AGENT" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  run grep -F 'AI_CONTAINER="mykg-opencode-daemon"' "$sync_script"
  [ "$status" -eq 0 ]
  run grep -F 'opencode_daemon.py' "$sync_script"
  [ "$status" -eq 0 ]

  run grep -F 'AI_CONTAINER="mykg-agy-daemon"' "$sync_script"
  [ "$status" -eq 0 ]
  run grep -F 'agy_daemon.py' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "mykg_sync.sh propagates the runner's exit code through the cleanup trap" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  run env AI_AGENT=agy VENV_PYTHON=/nonexistent/python SKIP_SANDBOX=1 bash "$sync_script" update
  [ "$status" -ne 0 ]
  [[ "$output" == *"not found or not executable"* ]]

  # A runner that fails must surface its status, not be swallowed by cleanup's
  # `exit "$EXIT_CODE"` on the EXIT trap.
  runner="${BATS_TEST_TMPDIR}/runner"
  printf '#!/bin/sh\nexit 7\n' > "$runner"
  chmod +x "$runner"
  mkdir -p "${BATS_TEST_TMPDIR}/venv/bin"
  ln -sf "$runner" "${BATS_TEST_TMPDIR}/venv/bin/python"

  run env AI_AGENT=agy VENV_PYTHON="${BATS_TEST_TMPDIR}/venv/bin/python" SKIP_SANDBOX=1 \
    bash "$sync_script" update
  [ "$status" -eq 7 ]
}

@test "mykg_sync.sh rejects an unknown mode and an unset AI_AGENT" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  run env AI_AGENT=agy bash "$sync_script" bogus
  [ "$status" -ne 0 ]
  [[ "$output" == *"unknown mode"* ]]

  run env -u AI_AGENT bash "$sync_script" update
  [ "$status" -ne 0 ]
  [[ "$output" == *"AI_AGENT must be set"* ]]
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
  [[ "$output" == *"opencode-go/longcat-2.5-preview-free"* ]]
  [[ "$output" == *"agent-opencode"* ]]
  [[ "$output" == *"scripts/mykg_sync.sh update"* ]]
}

@test "Makefile opencode default model is a live registry entry" {
  # Guards against the class of regression where the pinned default was
  # retired from the provider and every opencode mykg run failed.
  model=$(make -n mykg-update AI_AGENT=opencode 2>/dev/null | grep -o 'MYKG_MODEL="[^"]*"' | head -1 | cut -d'"' -f2)
  [ -n "$model" ]

  run opencode models
  [ "$status" -eq 0 ]
  [[ "$output" == *"$model"* ]]
}

@test "Makefile mykg-update preserves agy defaults when AI_AGENT=agy" {
  run make -n mykg-update
  [ "$status" -eq 0 ]
  [[ "$output" == *"gemini-3.8-flash-low"* ]]
  [[ "$output" == *"agent-claude-code"* ]]
  [[ "$output" == *"scripts/mykg_sync.sh update"* ]]
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

@test "opencode daemon does not pass v1-only CLI flags" {
  # opencode v2 removed --pure and --variant from `opencode run`. Passing
  # either makes the CLI print its usage block and exit 1 on every task, so
  # the model is never contacted and the whole extraction degrades silently.
  daemon_py="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"
  [ -f "$daemon_py" ]

  run grep -E '"--pure"' "$daemon_py"
  [ "$status" -ne 0 ]

  run grep -E '"--variant"' "$daemon_py"
  [ "$status" -ne 0 ]
}

@test "opencode daemon builds the model with a #variant suffix" {
  daemon_py="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"

  run grep -F 'def build_model_spec' "$daemon_py"
  [ "$status" -eq 0 ]
}

@test "mykg_sync.sh surfaces daemon start failures" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  # The daemon start must not be wrapped in `|| true`; a sandbox that never
  # came up used to look identical to a healthy run.
  run grep -F 'failed to start the ${AI_AGENT} extraction daemon' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "opencode harness probe never touches mykg session state" {
  probe_script="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"
  [ -f "$probe_script" ]
  [ -x "$probe_script" ]

  # The whole point of the probe is to test models without writing .error
  # envelopes, which is_task_done() treats as terminal. It must never point the
  # daemon at a real session inbox/outbox nor run the extraction pipeline.
  run grep -E 'agent_inbox|agent_outbox' "$probe_script"
  [ "$status" -ne 0 ]

  run grep -E 'run_update\.py|run_index\.py' "$probe_script"
  [ "$status" -ne 0 ]

  # It must exercise the real credential bootstrap, not a reimplementation.
  run grep -F 'bootstrap_opencode_auth' "$probe_script"
  [ "$status" -eq 0 ]

  # The egress proxy picks its allowlist from AI_AGENT, so it must be exported
  # for compose to interpolate it into the proxy service.
  run grep -E '^export AI_AGENT=opencode' "$probe_script"
  [ "$status" -eq 0 ]
}

@test "mykg-retry target re-queues failed agent tasks" {
  run make -n mykg-retry
  [ "$status" -eq 0 ]
  [[ "$output" == *"retry_failed.py"* ]]

  run make -n mykg-probe
  [ "$status" -eq 0 ]
  [[ "$output" == *"probe_opencode_harness.sh"* ]]
}

@test "mykg_sync.sh drains the agent queue before teardown" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  # The daemon is a consumer; without an explicit drain the EXIT trap removes
  # it while tasks are still pending, and those tasks end up with neither an
  # answer nor an error -- invisible, permanent data loss.
  run grep -F 'mykg_sync: agent queue drained' "$sync_script"
  [ "$status" -eq 0 ]

  run grep -F 'MYKG_DRAIN_TIMEOUT' "$sync_script"
  [ "$status" -eq 0 ]

  # The drain must be skippable, e.g. for a quick sync.
  run grep -E '\$\{MYKG_DRAIN:-1\}' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "mykgconfig.yaml includes agent-opencode profile" {
  config_file="${BATS_TEST_DIRNAME}/../../mykg_config.yaml"
  [ -f "$config_file" ]

  run grep -E "agent-opencode:" "$config_file"
  [ "$status" -eq 0 ]

  run grep -E "opencode-go/space-bunny-free" "$config_file"
  [ "$status" -eq 0 ]

  # The documented model must be free-tier: a missing OPENCODE_MODEL must never
  # silently start spending the operator's inference budget.
  run grep -E "opencode-go/(muse-spark|glm-|mimo-|grok-)" "$config_file"
  [ "$status" -ne 0 ]
}


@test "opencode defaults are free-tier" {
  daemon_py="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"
  probe="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"
  makefile="${BATS_TEST_DIRNAME}/../../Makefile"

  # A probe performs real billed calls, so its default model set must be free.
  # Comments are stripped first: the probe documents paid models as opt-in
  # examples, and naming one there is not the same as defaulting to it.
  run bash -c "grep -vE '^[[:space:]]*#' '$probe' | grep -E 'opencode-go/(muse-spark|glm-|mimo-v|grok-|gpt-6|deepseek-v4)'"
  [ "$status" -ne 0 ]

  # Same for the daemon's last-resort fallback, which is reached whenever the
  # environment names no model.
  run bash -c "grep -vE '^[[:space:]]*#' '$daemon_py' | grep -E '^DEFAULT_MODEL = \"opencode-go/(muse-spark|glm-|mimo-v|grok-|gpt-6|deepseek-v4)'"
  [ "$status" -ne 0 ]

  run grep -E 'OPENCODE_DEFAULT_MODEL \?= opencode-go/(muse-spark|glm-|mimo-v|grok-|gpt-6|deepseek-v4)' "$makefile"
  [ "$status" -ne 0 ]
}

@test "mykg_sync.sh raises daemon concurrency above one" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  # One worker means a single slow task blocks the queue for its full
  # timeout_seconds, which exceeds a default drain window.
  run grep -F 'MYKG_DAEMON_WORKERS' "$sync_script"
  [ "$status" -eq 0 ]

  run grep -F -- '--workers "$DAEMON_WORKERS"' "$sync_script"
  [ "$status" -eq 0 ]

  # The drain must report completions, not only the outstanding count.
  run grep -F 'no completions in the last' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "probe cleanup does not tear down a concurrent run" {
  probe="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"

  # `docker compose down` removes every service in the project, including the
  # egress proxy and extraction daemon of a concurrently running mykg-update,
  # which then fails in-flight tasks with a DNS timeout against the vanished
  # proxy. The probe must only undo what it started.
  # Comments are stripped: the script documents this hazard in prose, and
  # naming the forbidden command in a comment is not calling it.
  run bash -c "grep -vE '^[[:space:]]*#' '$probe' | grep -F 'compose down'"
  [ "$status" -ne 0 ]

  run bash -c "grep -vE '^[[:space:]]*#' '$probe' | grep -F 'compose -f \"\$COMPOSE_FILE\" down'"
  [ "$status" -ne 0 ]

  # It must track whether it started the proxy before stopping it.
  run grep -F 'STARTED_PROXY' "$probe"
  [ "$status" -eq 0 ]
}

@test "mykg drain guard locates the daemon by compose service, not container name" {
  sync_script="${BATS_TEST_DIRNAME}/../../scripts/mykg_sync.sh"

  # `compose run` does not reliably honour --name, so an exact container-name
  # match silently skipped the drain -- precisely when it is most needed.
  run grep -F 'com.docker.compose.service=' "$sync_script"
  [ "$status" -eq 0 ]

  run grep -F 'grep -qx "$AI_CONTAINER"' "$sync_script"
  [ "$status" -ne 0 ]

  # A drain that cannot start must say so rather than reporting success.
  run grep -F 'skipping queue drain' "$sync_script"
  [ "$status" -eq 0 ]
}

@test "opencode invocation uses standalone mode" {
  daemon_py="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/opencode_daemon.py"
  probe_model="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/probe_model.py"
  probe="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"

  # Without --standalone, `opencode run` connects to the long-lived background
  # service. In the container the equivalent private server deadlocks
  # intermittently after its database bootstrap.
  run grep -F '"--standalone"' "$daemon_py"
  [ "$status" -eq 0 ]

  run grep -F '"--standalone"' "$probe_model"
  [ "$status" -eq 0 ]

  run grep -F 'probe_model.py' "$probe"
  [ "$status" -eq 0 ]
}

@test "probe captures diagnostics before the container is removed" {
  probe_model="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/probe_model.py"

  # An intermittent hang leaves no evidence once `compose run --rm` has
  # removed the container, so the probe must dump state from inside.
  run grep -F 'subprocess.TimeoutExpired' "$probe_model"
  [ "$status" -eq 0 ]

  run grep -F 'dump_diagnostics' "$probe_model"
  [ "$status" -eq 0 ]

  run grep -F '/proc' "$probe_model"
  [ "$status" -eq 0 ]
}

@test "probe waits for proxy health instead of a fixed sleep" {
  probe="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"

  # The probe runs the agent with --no-deps, which bypasses compose's
  # depends_on/service_healthy gate. A fixed sleep therefore let opencode start
  # against a cold proxy and hang reaching the model catalogue. mykg_sync.sh is
  # not affected: it starts the daemon without --no-deps.
  run grep -F 'wait_for_proxy' "$probe"
  [ "$status" -eq 0 ]

  run grep -F 'State.Health.Status' "$probe"
  [ "$status" -eq 0 ]

  run bash -c "grep -vE '^[[:space:]]*#' '$probe' | grep -F 'sleep 4'"
  [ "$status" -ne 0 ]
}

@test "probe surfaces hang diagnostics instead of one line" {
  probe="${BATS_TEST_DIRNAME}/../../scripts/probe_opencode_harness.sh"

  # Collapsing output to `tail -1` discarded the very evidence the hang dump
  # exists to produce.
  run grep -F 'hang diagnostics' "$probe"
  [ "$status" -eq 0 ]
}

@test "probe avoids the inherited-pipe hang" {
  probe_model="${BATS_TEST_DIRNAME}/../../.agents/skills/iqoqo-mykg/scripts/probe_model.py"

  # `opencode run` spawns `serve --stdio`. If that server lingers after the
  # client exits, it keeps the inherited stdout/stderr pipe write end open, and
  # subprocess.run(capture_output=True) blocks forever waiting for EOF on a pipe
  # whose writer is an orphaned process -- an indefinite hang with no live
  # child to explain it. Temp files sidestep it; the daemon already does this.
  run bash -c "grep -vE '^[[:space:]]*#' '$probe_model' | grep -F 'capture_output=True'"
  [ "$status" -ne 0 ]

  run grep -F 'TemporaryFile' "$probe_model"
  [ "$status" -eq 0 ]

  run grep -F 'subprocess.DEVNULL' "$probe_model"
  [ "$status" -eq 0 ]
}
