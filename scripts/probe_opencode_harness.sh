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
if docker ps --format '{{.Names}}' | grep -q 'egress-proxy'; then
  :
else
  docker compose -f "$COMPOSE_FILE" up -d sandbox-egress-proxy >/dev/null 2>&1 || true
  STARTED_PROXY=1
fi
sleep 4

# Host control. Without this the output is ambiguous: "Model unavailable" could
# mean a bad model name OR a broken sandbox. Running the same model on the host
# first separates the two — if the host answers and the sandbox does not, the
# model is fine and the harness environment is the problem.
if [ "${PROBE_SKIP_HOST:-0}" != "1" ]; then
  HOST_SPEC="${MODELS[0]}#${VARIANT}"
  printf '%-52s ' "[host control] $HOST_SPEC"
  if HOST_OUT=$(opencode run --auto -m "$HOST_SPEC" "$PROMPT" 2>&1); then
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

  # Run the real bootstrap so auth is placed exactly where the daemon puts it.
  OUT=$(docker compose -f "$COMPOSE_FILE" run --rm -T --no-deps \
    -v "$AI_BIN:/usr/local/bin/opencode:ro" \
    -e "OPENCODE_MODEL=$SPEC" \
    "$SERVICE" \
    python3 -c "
import subprocess, sys
sys.path.insert(0, '/workspace/.agents/skills/iqoqo-mykg/scripts')
from opencode_daemon import bootstrap_opencode_auth, build_subprocess_env
bootstrap_opencode_auth()
model = '$SPEC'
# Use the daemon's own env builder so the probe exercises the exact code path
# extraction uses, including the opencode-go API key injection. A hand-rolled
# env here would test something the daemon never does.
r = subprocess.run(
    ['opencode', 'run', '--auto', '-m', model, '''$PROMPT'''],
    capture_output=True, text=True, timeout=300,
    env=build_subprocess_env(model),
)
sys.stdout.write(r.stdout[-400:])
sys.stderr.write(r.stderr[-400:])
sys.exit(r.returncode)
" 2>&1) && RC=0 || RC=$?

  if [ "$RC" -eq 0 ]; then
    printf 'OK\n'
    PASSED=$((PASSED + 1))
  else
    # Collapse to the last non-empty stderr line; the useful part of an opencode
    # failure is on one line, and the usage block is dozens.
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
