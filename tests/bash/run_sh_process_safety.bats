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
# MOD-OPS-02 / MOD-OPS-03: run.sh process-safety contract.
#
# Sources only the two functions under test out of run.sh, which is a large
# script with top-level side effects (cd, mode parsing, process spawning) and
# cannot be executed directly in a test.

RUN_SH="${BATS_TEST_DIRNAME}/../../run.sh"

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
  cd "$TEST_TEMP_DIR"
}

teardown() {
  cd /tmp
  rm -rf "$TEST_TEMP_DIR"
}

# Extract `update_env_var` from run.sh (from its definition to the closing brace
# at column 0) and evaluate it in this shell.
#
# `tighten_env_permissions` must be loaded too: update_env_var calls it to
# narrow a secrets file's mode, and the awk extractor stops at the first
# column-0 `}` so it cannot pull in a dependency by itself.
load_update_env_var() {
  local fn perms
  fn=$(awk '/^update_env_var\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [ -n "$fn" ] || { echo "failed to extract update_env_var from run.sh" >&2; return 1; }
  perms=$(awk '/^tighten_env_permissions\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [ -n "$perms" ] || { echo "failed to extract tighten_env_permissions from run.sh" >&2; return 1; }
  eval "$perms"
  eval "$fn"
}
# Extract `terminate_from_pidfile` from run.sh.
load_terminate_from_pidfile() {
  local fn
  fn=$(awk '/^terminate_from_pidfile\(\) \{$/{f=1} f{print} f&&/^\}$/{exit}' "$RUN_SH")
  [ -n "$fn" ] || { echo "failed to extract terminate_from_pidfile from run.sh" >&2; return 1; }
  eval "$fn"
}

# ───────────────────────── MOD-OPS-03 ─────────────────────────

@test "update_env_var creates a timestamped backup before mutating .env" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env"
  printf 'SECRET_KEY="oldvalue"\nDB_PORT=5432\n' > "$env_file"

  update_env_var "$env_file" "SECRET_KEY" "newvalue"

  # The backup exists, is timestamped, and holds the PRE-mutation content.
  local backups
  backups=$(ls "$TEST_TEMP_DIR"/.env.bak.* 2>/dev/null)
  [ -n "$backups" ]
  grep -q 'SECRET_KEY="oldvalue"' "$backups"
  ! grep -q 'newvalue' "$backups"

  # The live file has the new value and kept its other keys.
  grep -q 'SECRET_KEY="newvalue"' "$env_file"
  grep -q 'DB_PORT=5432' "$env_file"
}

@test "update_env_var backup filename carries a YYYYMMDD_HHMMSS timestamp" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env"
  printf 'SECRET_KEY="old"\n' > "$env_file"

  update_env_var "$env_file" "SECRET_KEY" "new"

  local name
  name=$(basename "$(ls "$TEST_TEMP_DIR"/.env.bak.* | head -1)")
  [[ "$name" =~ ^\.env\.bak\.[0-9]{8}_[0-9]{6}$ ]]
}

@test "update_env_var does not duplicate an existing key" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env"
  printf 'SECRET_KEY="a"\n' > "$env_file"

  update_env_var "$env_file" "SECRET_KEY" "b"

  [ "$(grep -c '^SECRET_KEY=' "$env_file")" -eq 1 ]
}

@test "update_env_var appends a previously absent key" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env"
  printf 'DB_PORT=5432\n' > "$env_file"

  update_env_var "$env_file" "NEW_KEY" "value"

  grep -q '^NEW_KEY="value"' "$env_file"
  [ "$(ls "$TEST_TEMP_DIR"/.env.bak.* 2>/dev/null | wc -l)" -eq 1 ]
}

@test "update_env_var preserves no backup for a brand new empty file" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env.fresh"

  update_env_var "$env_file" "KEY" "value"

  grep -q '^KEY="value"' "$env_file"
  # Nothing to lose, so no backup is written.
  [ "$(ls "$TEST_TEMP_DIR"/.env.fresh.bak.* 2>/dev/null | wc -l)" -eq 0 ]
}

@test "update_env_var backup does not widen the permissions of a 0600 .env" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env"
  printf 'SECRET_KEY="old"\n' > "$env_file"
  chmod 0600 "$env_file"

  update_env_var "$env_file" "SECRET_KEY" "new"

  local backup
  backup=$(ls "$TEST_TEMP_DIR"/.env.bak.* | head -1)
  [ "$(stat -c '%a' "$backup")" = "600" ]
  [ "$(stat -c '%a' "$env_file")" = "600" ]
}

@test "update_env_var aborts rather than destroying secrets when no backup can be made" {
  load_update_env_var
  local subdir="${TEST_TEMP_DIR}/ro"
  mkdir -p "$subdir"
  local env_file="${subdir}/.env"
  printf 'SECRET_KEY="theonlycopy"\n' > "$env_file"

  # Simulate an unwritable directory (full disk, root-owned perms).
  # `cp` of a file to a new name needs +w on the directory, which is withheld.
  chmod 0555 "$subdir"

  run update_env_var "$env_file" "SECRET_KEY" "rotated"
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Refusing to rotate secrets" ]]

  # The original secrets are still intact and unmodified.
  grep -q 'SECRET_KEY="theonlycopy"' "$env_file"

  chmod 0755 "$subdir"
}

# ───────────────────────── MOD-OPS-02 ─────────────────────────

@test "run.sh graceful shutdown budget is 15 seconds, not 5" {
  # Assert on the shipped source rather than timing a real shutdown.
  run grep -E 'grace="\$\{IQOQO_GRACEFUL_SHUTDOWN_SECONDS:-15\}"' "$RUN_SH"
  [ "$status" -eq 0 ]
}

@test "terminate_from_pidfile waits the full grace period before SIGKILL" {
  load_terminate_from_pidfile

  # A process that traps and ignores SIGTERM stands in for a busy gunicorn
  # worker draining in-flight requests. It must survive the grace window
  # (proving no early SIGKILL) and be killed once the budget elapses.
  local pidfile="${TEST_TEMP_DIR}/worker.pid"
  bash -c 'trap "" TERM; sleep 60' &
  local pid=$!
  echo "$pid" > "$pidfile"
  trap 'kill -9 '"$pid"' 2>/dev/null || true' RETURN

  local start elapsed
  start=$(date +%s)
  IQOQO_GRACEFUL_SHUTDOWN_SECONDS=6 terminate_from_pidfile "$pidfile" "test worker" >/dev/null 2>&1
  elapsed=$(( $(date +%s) - start ))

  # Waited at least the configured budget, and killed once the budget elapsed.
  [ "$elapsed" -ge 6 ]
  ! kill -0 "$pid" 2>/dev/null
  [ ! -f "$pidfile" ]
}

@test "terminate_from_pidfile returns immediately for an already-dead pid" {
  load_terminate_from_pidfile
  local pidfile="${TEST_TEMP_DIR}/gone.pid"
  echo 999999 > "$pidfile"

  local start elapsed
  start=$(date +%s)
  terminate_from_pidfile "$pidfile" "gone process"
  elapsed=$(( $(date +%s) - start ))

  # No waiting: the pid does not exist, so the stale pidfile is just cleaned up.
  [ "$elapsed" -lt 3 ]
  [ ! -f "$pidfile" ]
}

@test "terminate_from_pidfile cleans up a stale pidfile with an empty body" {
  load_terminate_from_pidfile
  local pidfile="${TEST_TEMP_DIR}/empty.pid"
  : > "$pidfile"

  run terminate_from_pidfile "$pidfile" "empty pidfile"
  [ "$status" -eq 0 ]
  [ ! -f "$pidfile" ]
}

# ───────────────────── tracked-file guard and escaping ─────────────────────

@test "update_env_var refuses to write a secret into a version-controlled file" {
  load_update_env_var
  local repo="${TEST_TEMP_DIR}/repo"
  mkdir -p "$repo"
  (
    cd "$repo"
    git init -q .
    echo "SECRET_KEY=old" > .env.test
    git add .env.test
  )

  # Run inside the throwaway repo so `git ls-files` reports the file as tracked.
  run bash -c "cd '$repo' && source /dev/stdin <<'EOF'
$(declare -f update_env_var tighten_env_permissions)
update_env_var '.env.test' 'SECRET_KEY' 'rotated-value'
EOF"
  [ "$status" -ne 0 ]
  [[ "$output" == *"version-controlled"* ]]
  # The original value must survive: a refused rotation must not half-apply.
  grep -q "SECRET_KEY=old" "$repo/.env.test"
}

@test "update_env_var allows an untracked file" {
  load_update_env_var
  local repo="${TEST_TEMP_DIR}/repo2"
  mkdir -p "$repo"
  (
    cd "$repo"
    git init -q .
    echo "SECRET_KEY=old" > .env
  )

  run bash -c "cd '$repo' && source /dev/stdin <<'EOF'
$(declare -f update_env_var tighten_env_permissions)
update_env_var '.env' 'SECRET_KEY' 'rotated-value'
EOF"
  [ "$status" -eq 0 ]
  grep -q "rotated-value" "$repo/.env"
}

@test "update_env_var escapes shell metacharacters in a value" {
  # The env file is later read with `source` under `set -o allexport`, so an
  # unescaped backtick or $(...) in a value becomes command execution as the
  # deploying user. Values here can originate in an HTTP response body.
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env.escape"
  echo "EXISTING=1" > "$env_file"

  update_env_var "$env_file" "TOKEN" 'a`touch pwned`b$(touch pwned2)c$d"e'

  # Sourcing must not execute anything, and must restore the value exactly.
  local roundtrip
  roundtrip=$(bash -c "set -a; . '$env_file'; set +a; printf '%s' \"\$TOKEN\"")
  [ "$roundtrip" = 'a`touch pwned`b$(touch pwned2)c$d"e' ]
  [ ! -f "./pwned" ]
  [ ! -f "./pwned2" ]
  # The stored form must carry the escapes, not the raw metacharacters.
  grep -q 'TOKEN="a\\`' "$env_file"
}

@test "update_env_var tightens a secrets file to 0600" {
  load_update_env_var
  local env_file="${TEST_TEMP_DIR}/.env.perms"
  echo "EXISTING=1" > "$env_file"
  chmod 0664 "$env_file"

  update_env_var "$env_file" "SECRET_KEY" "a-secret-value"

  [ "$(stat -c '%a' "$env_file")" = "600" ]
}
