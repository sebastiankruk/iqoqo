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
# mykg_sync.sh — Drive the myKG index/update pipeline with a Docker AI sandbox
#
# MOD-OPS-04: this logic used to live inline in the `mykg-update` and
# `mykg-index` Makefile recipes. That was ~45 lines of multi-line shell
# continuation per target, duplicated between the two with a one-token
# difference (the inbox/outbox paths). Consequences:
#   * Make expands every line as a separate shell unless escaped, so a single
#     missing backslash silently split one command into two, and a `#` comment
#     or `$$` in the body was consumed by make rather than by bash;
#   * the sandbox teardown logic existed twice and had to be kept in sync by
#     hand;
#   * `make -n` could not show what the target actually did, and nothing could
#     unit-test the trap behaviour.
# Moving it here makes it lintable with shellcheck, testable with bats, and
# keeps the Makefile as a thin, readable wrapper.
#
# Usage:
#   scripts/mykg_sync.sh update [extra args...]   # incremental graph update
#   scripts/mykg_sync.sh index  [extra args...]   # full reindex
#
# Environment:
#   AI_AGENT   agy | opencode            (required; selects the daemon binary)
#   MYKG_MODEL / MYKG_EFFORT             model + effort passed to the agent
#   MYKG_PROFILE                         profile name for the python runner
#   VENV_PYTHON                          python interpreter (default .venv/bin/python)
#   SKIP_SANDBOX=1                       skip Docker sandbox startup entirely
# =============================================================================

set -euo pipefail

MODE="${1:-}"
if [ -z "$MODE" ]; then
  echo "Usage: $0 {update|index} [args...]" >&2
  exit 2
fi
shift || true

case "$MODE" in
  update|index) ;;
  *)
    echo "mykg_sync: unknown mode '${MODE}' (expected 'update' or 'index')" >&2
    exit 2
    ;;
esac

AI_AGENT="${AI_AGENT:-}"
if [ -z "$AI_AGENT" ]; then
  echo "mykg_sync: AI_AGENT must be set to 'agy' or 'opencode'." >&2
  exit 2
fi

# Exported once, here, rather than as a `VAR=x docker ...` prefix on each
# call. docker compose reads AI_AGENT from the environment to choose the
# egress-proxy allowlist, and a prefix assignment is visible only to the
# forked process — so the very next `-e AI_AGENT="$AI_AGENT"` would expand the
# *outer* value, which shellcheck flags as SC2097/SC2098. Exporting states the
# intent once and removes the trap.
export AI_AGENT

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
COMPOSE_FILE="docker-compose.ai_sandbox.yml"
SKILL_SCRIPTS=".agents/skills/iqoqo-mykg/scripts"

if [ ! -x "$VENV_PYTHON" ]; then
  echo "mykg_sync: ${VENV_PYTHON} not found or not executable. Run 'make dev-setup' or create the venv." >&2
  exit 1
fi

# ── Sandbox lifecycle ───────────────────────────────────────────────────────
# Registered before anything is started so a Ctrl-C, a failure, or `set -e`
# firing mid-run always tears the daemon and the compose stack down. Leaking a
# detached daemon container between runs causes the *next* run's
# `docker rm -f` to be load-bearing, and a leaked egress proxy keeps an
# allowlisting proxy alive with no consumer.
cleanup() {
  EXIT_CODE=$?
  trap - EXIT INT TERM
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" down >/dev/null 2>&1 || true
    docker rm -f mykg-agy-daemon >/dev/null 2>&1 || true
    docker rm -f mykg-opencode-daemon >/dev/null 2>&1 || true
  fi
  exit "$EXIT_CODE"
}
trap cleanup EXIT INT TERM

docker_available() {
  command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

# Resolve which agent binary and daemon container this run should use.
case "$AI_AGENT" in
  opencode)
    AI_BIN="$(command -v opencode 2>/dev/null || echo "")"
    AI_CONTAINER="mykg-opencode-daemon"
    AI_MOUNT="/usr/local/bin/opencode:ro"
    AI_SCRIPT="${SKILL_SCRIPTS}/opencode_daemon.py"
    ;;
  agy)
    AI_BIN="$(command -v agy 2>/dev/null || echo "")"
    AI_CONTAINER="mykg-agy-daemon"
    AI_MOUNT="/usr/local/bin/agy:ro"
    AI_SCRIPT="${SKILL_SCRIPTS}/agy_daemon.py"
    ;;
  *)
    echo "mykg_sync: invalid AI_AGENT '${AI_AGENT}' (expected 'agy' or 'opencode')." >&2
    exit 2
    ;;
esac

# `update` only works against the newest session's inbox/outbox; `index`
# operates on the whole `mykg_sessions` tree.
INBOX=""
OUTBOX=""
if [ "$MODE" = "update" ]; then
  # Resolve the newest session directory. `sys.exit(0)` with no output when
  # there are none, which is the signal to skip sandbox startup entirely
  # (there is nothing to drain) while still running the python runner.
  SESS_DIR="$("$VENV_PYTHON" -c "
import pathlib, sys
p = pathlib.Path('mykg_sessions')
target = p.resolve() if p.exists() else pathlib.Path('.mykg_sessions').resolve()
sessions = sorted([d for d in target.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True) if target.exists() else []
print(str(sessions[0])) if sessions else sys.exit(0)
")"

  if [ -n "$SESS_DIR" ]; then
    INBOX="mykg_sessions/$(basename "$SESS_DIR")/intermediate/agent_inbox"
    OUTBOX="mykg_sessions/$(basename "$SESS_DIR")/intermediate/agent_outbox"
    mkdir -p "$INBOX" "$OUTBOX"
  fi
else
  mkdir -p "mykg_sessions"
  INBOX="mykg_sessions"
  OUTBOX="mykg_sessions"
fi

start_sandbox_daemon() {
  # No agent binary on PATH, or explicitly disabled: run the python runner
  # directly. It degrades to non-LLM extraction tiers rather than failing.
  if [ -z "$AI_BIN" ]; then
    echo "mykg_sync: '${AI_AGENT}' binary not on PATH; running without the AI sandbox." >&2
    return 0
  fi

  # Pre-flight removal: a daemon left over from an interrupted run would
  # otherwise make `docker run --name` fail with a name conflict.
  docker rm -f "$AI_CONTAINER" >/dev/null 2>&1 || true

  # Recreate the egress proxy so its allowlist is re-read and it is not
  # serving a stale configuration.
  #
  # AI_AGENT is exported once here rather than written as a `VAR=x docker ...`
  # prefix on every call. A prefix assignment is only visible to the forked
  # process, so a `-e AI_AGENT="$AI_AGENT"` on the *same* command line would
  # expand the outer value and shellcheck (rightly) flags the combination
  # SC2097/SC2098. Exporting makes the intent explicit and removes the trap.
  docker compose -f "$COMPOSE_FILE" stop sandbox-egress-proxy >/dev/null 2>&1 || true
  docker compose -f "$COMPOSE_FILE" rm -f sandbox-egress-proxy >/dev/null 2>&1 || true
  docker compose -f "$COMPOSE_FILE" up -d sandbox-egress-proxy >/dev/null 2>&1 || true

  # A failing daemon start is fatal rather than ignored. The previous
  # `>/dev/null 2>&1 || true` made a daemon that never started -- or started
  # and died on every task -- indistinguishable from a healthy run, which is
  # how a hard opencode CLI regression went unnoticed. A non-zero status here
  # means the sandbox never came up, so the extraction would silently degrade
  # to the non-LLM tiers and quietly produce a worse knowledge graph.
  # Concurrency. A single worker means one slow task parks the whole queue for
  # up to its own timeout_seconds (1800s in practice) -- longer than a typical
  # drain window -- so one bad task silently stalls the entire backlog. Two
  # matches the daemon's own default and stays under provider rate limits.
  DAEMON_WORKERS="${MYKG_DAEMON_WORKERS:-2}"
  if ! docker compose -f "$COMPOSE_FILE" run --rm -d --name "$AI_CONTAINER" \
    -v "$AI_BIN:$AI_MOUNT" \
    -e MYKG_MODEL="${MYKG_MODEL:-}" \
    -e MYKG_EFFORT="${MYKG_EFFORT:-}" \
    -e OPENCODE_MODEL="${MYKG_MODEL:-}" \
    -e OPENCODE_EFFORT="${MYKG_EFFORT:-}" \
    -e AI_AGENT="$AI_AGENT" \
    "$AI_CONTAINER" \
    python3 "$AI_SCRIPT" \
    --workers "$DAEMON_WORKERS" \
    "$INBOX" \
    "$OUTBOX"; then
    echo "mykg_sync: failed to start the ${AI_AGENT} extraction daemon." >&2
    echo "mykg_sync: inspect it with:" >&2
    echo "  docker logs $AI_CONTAINER" >&2
    return 1
  fi
}

if [ "${SKIP_SANDBOX:-0}" != "1" ] && docker_available && [ -n "$INBOX" ]; then
  start_sandbox_daemon
else
  [ -n "$INBOX" ] || echo "mykg_sync: no mykg sessions found; running the updater without a sandbox." >&2
fi

# ── Run the pipeline ────────────────────────────────────────────────────────
if [ "$MODE" = "update" ]; then
  RUNNER="${SKILL_SCRIPTS}/run_update.py"
else
  RUNNER="${SKILL_SCRIPTS}/run_index.py"
fi

# A non-zero exit here propagates: `set -e` plus the EXIT trap preserves the
# original status through cleanup's `exit "$EXIT_CODE"`.
MYKG_PROFILE="${MYKG_PROFILE:-}" "$VENV_PYTHON" "$RUNNER" "$@"

# ── Drain the agent queue ───────────────────────────────────────────────────
# The extraction runner is the producer; the daemon is a consumer that runs
# alongside it. The runner returns as soon as extraction finishes, and the EXIT
# trap then removes the daemon container -- so any tasks still sitting in the
# inbox are abandoned mid-flight. That silently converts inference work into
# "no result at all": the tasks stay pending with neither an answer nor an
# error, so nothing reports the loss and the graph is quietly incomplete.
#
# Wait here for the queue to drain before teardown. Bounded, and only when a
# daemon is actually running and there is something to drain.
DRAIN_TIMEOUT="${MYKG_DRAIN_TIMEOUT:-900}"
if [ "$MODE" = "update" ] && [ -n "$INBOX" ] && [ "${MYKG_DRAIN:-1}" = "1" ] \
   && [ "${SKIP_SANDBOX:-0}" != "1" ] && [ -n "$AI_CONTAINER" ] \
   && docker ps --format '{{.Names}}' | grep -qx "$AI_CONTAINER"; then

  count_unfinished() {
    # A task is unfinished while it has no answer and no error envelope.
    find "$INBOX" -maxdepth 1 -name '*.task.json' 2>/dev/null | while read -r task; do
      id="$(basename "$task" .task.json)"
      if [ ! -f "$OUTBOX/$id.answer.json" ] && [ ! -f "$OUTBOX/$id.done" ] && [ ! -f "$OUTBOX/$id.error" ]; then
        printf 'x'
      fi
    done | wc -c | tr -d ' '
  }

  ELAPSED=0
  LAST_REPORT=0
  LAST_PENDING="$(count_unfinished)"
  STARTED_UNFINISHED="$LAST_PENDING"
  STALLED_REPORTED=0
  while :; do
    PENDING="$(count_unfinished)"
    [ "$PENDING" = "0" ] && break
    if [ "$ELAPSED" -ge "$DRAIN_TIMEOUT" ]; then
      COMPLETED=$((STARTED_UNFINISHED - PENDING))
      echo "mykg_sync: drain timed out after ${DRAIN_TIMEOUT}s." >&2
      echo "mykg_sync:   completed $COMPLETED, still pending $PENDING." >&2
      echo "mykg_sync: re-run 'make mykg-update' to continue, or raise MYKG_DRAIN_TIMEOUT." >&2
      break
    fi
    if [ $((ELAPSED - LAST_REPORT)) -ge 60 ]; then
      # Report completions, not just the outstanding count. A repeated identical
      # pending count is indistinguishable from a stall unless the delta is
      # shown, which is how a single slow task can go unnoticed.
      COMPLETED=$((STARTED_UNFINISHED - PENDING))
      if [ "$PENDING" -eq "$LAST_PENDING" ] && [ "$STALLED_REPORTED" -eq 0 ]; then
        echo "mykg_sync: no completions in the last 60s with $PENDING task(s) pending." >&2
        echo "mykg_sync: the daemon may be blocked on a single slow task; check:" >&2
        echo "  docker logs $AI_CONTAINER" >&2
        STALLED_REPORTED=1
      fi
      echo "mykg_sync: draining $PENDING pending agent task(s) (completed $COMPLETED)..."
      LAST_REPORT="$ELAPSED"
      LAST_PENDING="$PENDING"
    fi
    sleep 10
    ELAPSED=$((ELAPSED + 10))
  done

  if [ "$PENDING" = "0" ] && [ "$ELAPSED" -gt 0 ]; then
    echo "mykg_sync: agent queue drained after ${ELAPSED}s (completed $((STARTED_UNFINISHED - PENDING)))."
  fi
  unset -f count_unfinished
fi
