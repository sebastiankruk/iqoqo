#!/usr/bin/env bash
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# =============================================================================
# probe_opencode_harness.sh — Test opencode model calls INSIDE the AI sandbox
#
# WHY THIS EXISTS
#   `make mykg-update` is a bad way to find out whether the opencode harness
#   works. Every failed task writes a terminal .error envelope that
#   is_task_done() treats as finished, so a probe run silently and permanently
#   poisons real extraction work. This script never touches mykg_sessions.
#
#   It replicates the sandbox faithfully — same compose service, same image,
#   same read-only rootfs, same cap_drop, same egress proxy, same surgical
#   auth.json mount — and then calls `opencode run` directly. A real model
#   answering here means a real API call, visible on the opencode.ai side.
#
#   The credential is bootstrapped by calling the daemon's own
#   bootstrap_opencode_auth(), not a reimplementation, so the probe exercises
#   the same auth path the extraction daemon uses.
#
# Usage:
#   scripts/probe_opencode_harness.sh                      # default model set
#   scripts/probe_opencode_harness.sh opencode-go/glm-5.3 opencode-go/qwen3.8-flash
#   PROBE_VARIANT=high scripts/probe_opencode_harness.sh   # different variant
#   PROBE_PROMPT="say OK" scripts/probe_opencode_harness.sh
#
# Exit status: 0 if every model succeeded, 1 otherwise.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="docker-compose.ai_sandbox.yml"
SERVICE="mykg-opencode-daemon"
VARIANT="${PROBE_VARIANT:-low}"
PROMPT="${PROBE_PROMPT:-reply with the single word OK}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-120}"

# Models are passed as provider/model; the variant is appended as the v2
# '#suffix'. Keep the defaults in the provider namespace that auth.json
# actually covers (opencode-go) — the 'opencode' namespace is a different
# account and will fail for reasons unrelated to the harness.
#
# The default set is deliberately FREE-TIER ONLY. A probe performs real billed
# calls, and only two models on this provider cost nothing; probing a paid
# model by default would spend the operator's budget without them asking. Pass
# a model explicitly to test anything else:
#   make mykg-probe ARGS="opencode-go/glm-5.3-flash"
#
# Of the two free models, only space-bunny-free publishes variants, so it is the
# only one that can be probed with a variant suffix. longcat-2.5-preview-free
# publishes none, so appending one can never succeed for it.
MODELS=("$@")
if [ ${#MODELS[@]} -eq 0 ]; then
  MODELS=(
    "opencode-go/space-bunny-free"
  )
fi

# The proxy picks its allowlist from AI_AGENT, so it must be exported here for
# compose to interpolate into the sandbox-egress-proxy service.
export AI_AGENT=opencode

cleanup() {
  EXIT_CODE=$?
  trap - EXIT INT TERM
  # Deliberately NOT `docker compose down`. That tears down every service in
  # the project -- including the egress proxy and the extraction daemon of any
  # concurrently running `make mykg-update`, which then fails every in-flight
  # task with a DNS timeout against the vanished proxy. This script's own
  # containers are already removed by `run --rm`; the proxy is only stopped
  # when this script was the one that started it.
  if [ "$STARTED_PROXY" = "1" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" stop sandbox-egress-proxy >/dev/null 2>&1 || true
  fi
  exit "$EXIT_CODE"
}
trap cleanup EXIT INT TERM

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "probe: docker is not available; cannot test the sandbox harness." >&2
  exit 1
fi

AI_BIN="$(command -v opencode 2>/dev/null || true)"
if [ -z "$AI_BIN" ]; then
  echo "probe: 'opencode' binary not found on PATH; the sandbox mounts it from here." >&2
  exit 1
fi

if [ ! -f "$HOME/.local/share/opencode/auth.json" ]; then
  echo "probe: ~/.local/share/opencode/auth.json not found." >&2
  echo "probe: the compose mount will create a directory there and auth will be missing." >&2
  exit 1
fi

echo "=== opencode sandbox harness probe ==="
echo "variant : $VARIANT"
echo "prompt  : $PROMPT"
echo "models  : ${#MODELS[@]}"
echo "NOTE: each successful model makes a real billed API call."
echo

# Track whether the proxy was already up, so cleanup leaves a proxy it did not
# start alone. Never run `docker compose down` here.
STARTED_PROXY=0
if ! docker ps --format '{{.Names}}' | grep -q 'egress-proxy'; then
  docker compose -f "$COMPOSE_FILE" up -d sandbox-egress-proxy >/dev/null 2>&1 || true
  STARTED_PROXY=1
fi

# Wait for the proxy to be genuinely healthy. This probe runs the agent with
# --no-deps, which bypasses compose's depends_on/service_healthy gate, so the
# readiness check has to be done here. A fixed sleep was the bug: a cold proxy
# can take longer than that to accept connections, and opencode then hangs
# trying to reach the model catalogue. mykg_sync.sh does not have this problem
# because it starts the daemon without --no-deps and compose waits for it.
wait_for_proxy() {
  local tries=0 cid status
  while [ "$tries" -lt 60 ]; do
    cid="$(docker ps -q --filter name=egress-proxy 2>/dev/null | head -1)"
    if [ -n "$cid" ]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null)"
      case "$status" in
        healthy|running) return 0 ;;
      esac
    fi
    sleep 1
    tries=$((tries + 1))
  done
  return 1
}

if wait_for_proxy; then
  :
else
  echo "probe: egress proxy did not become healthy; sandbox calls will fail." >&2
  echo "probe: inspect it with 'docker logs $(docker ps -q --filter name=egress-proxy | head -1)'." >&2
fi

# Host control. Without this the output is ambiguous: "Model unavailable" could
# mean a bad model name OR a broken sandbox. Running the same model on the host
# first separates the two — if the host answers and the sandbox does not, the
# model is fine and the harness environment is the problem.
if [ "${PROBE_SKIP_HOST:-0}" != "1" ]; then
  HOST_SPEC="${MODELS[0]}#${VARIANT}"
  printf '%-52s ' "[host control] $HOST_SPEC"
  # --standalone for the same reason as the daemon: no background server to wait on.
  if HOST_OUT=$(opencode run --standalone --auto -m "$HOST_SPEC" "$PROMPT" 2>&1); then
    printf 'OK\n'
  else
    REASON=$(printf '%s\n' "$HOST_OUT" | sed -E 's/\x1b\[[0-9;]*m//g' | grep -vE '^\s*$' | tail -1 | cut -c1-100)
    printf 'FAIL\n        %s\n' "${REASON:-<no output>}"
    echo "        ^ The model fails on the HOST too, so this is not a sandbox problem."
    echo "          Check the model name and the opencode-go credential before continuing."
  fi
  echo
fi

PASSED=0
FAILED=0
FAILED_MODELS=()

for MODEL in "${MODELS[@]}"; do
  SPEC="${MODEL}#${VARIANT}"
  printf '%-52s ' "$SPEC"

  # probe_model.py runs inside the container and uses the daemon's own
  # credential path. On a hang it dumps /proc, the opencode log and the proxy
  # env *before* `compose run --rm` removes the container -- the only way to
  # get evidence out of an intermittent hang.
  #
  # NOTE: no comment may sit inside the continuation below; bash would end the
  # command there and run the rest on the host.
  OUT=$(docker compose -f "$COMPOSE_FILE" run --rm -T --no-deps \
    -v "$AI_BIN:/usr/local/bin/opencode:ro" \
    -e "OPENCODE_MODEL=$SPEC" \
    "$SERVICE" \
    python3 /workspace/.agents/skills/iqoqo-mykg/scripts/probe_model.py \
      "$SPEC" "$PROMPT" "$PROBE_TIMEOUT" 2>&1) && RC=0 || RC=$?

  if [ "$RC" -eq 0 ]; then
    printf 'OK\n'
    PASSED=$((PASSED + 1))
  elif printf '%s' "$OUT" | grep -q 'HANG DIAGNOSTICS'; then
    # A hang dumped its own evidence. Show ALL of it: the process table and the
    # opencode log are the only record that survives, and collapsing to a
    # single line (as this used to do) throws the diagnosis away.
    printf 'HANG (rc=%s)\n' "$RC"
    echo "----- hang diagnostics -----"
    printf '%s\n' "$OUT" | sed -E 's/\x1b\[[0-9;]*m//g' | grep -vE "orphan containers|^\s*$" | cut -c1-190
    echo "----- end diagnostics -----"
    FAILED=$((FAILED + 1))
    FAILED_MODELS+=("$SPEC")
  else
    # Collapse to the last non-empty line; the useful part of an ordinary
    # opencode failure is on one line, and the usage block is dozens.
    REASON=$(printf '%s\n' "$OUT" | sed -E 's/\x1b\[[0-9;]*m//g' | grep -vE '^\s*$' | tail -1 | cut -c1-120)
    printf 'FAIL (rc=%s)\n' "$RC"
    echo "        ${REASON:-<no output>}"
    FAILED=$((FAILED + 1))
    FAILED_MODELS+=("$SPEC")
  fi
done

echo
echo "--------------------------------------------"
echo "passed: $PASSED   failed: $FAILED"
if [ "$FAILED" -gt 0 ]; then
  echo "failing models:"
  for M in "${FAILED_MODELS[@]}"; do
    echo "  - $M"
  done
  echo
  echo "The session outbox was NOT touched, so mykg state is unaffected."
  echo "If every model fails with 'Model unavailable', the harness cannot"
  echo "resolve the provider at all — that is an environment problem, not a"
  echo "model-selection problem."
fi

[ "$FAILED" -eq 0 ]
