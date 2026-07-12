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
#

# tests/bash/merge_env.bats
# Functional tests for scripts/merge_env.sh

bats_require_minimum_version 1.5.0

MERGE_ENV="./scripts/merge_env.sh"

setup() {
    TEST_DIR="$(mktemp -d)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ── CLI interface ───────────────────────────────────────────────

@test "merge_env.sh --help exits 1 and prints usage" {
  run bash "$MERGE_ENV" --help
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "merge_env.sh requires stage argument" {
  run bash "$MERGE_ENV"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "stage name required" ]]
}

@test "merge_env.sh rejects invalid stage name" {
  run bash "$MERGE_ENV" bogus
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Unknown option:" ]]
}

# ── Dry-run with test files ─────────────────────────────────────

@test "merge_env.sh preview --dry-run detects missing keys" {
  echo "KEY_A=alpha" > "$TEST_DIR/.env"
  echo "KEY_B=beta" > "$TEST_DIR/.env.preview"

  run bash "$MERGE_ENV" preview --root "$TEST_DIR" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "+ KEY_A=alpha" ]]
}

@test "merge_env.sh preview --dry-run target wins on conflict" {
  echo "KEY_A=from_env" > "$TEST_DIR/.env"
  echo "KEY_A=from_preview" > "$TEST_DIR/.env.preview"

  run bash "$MERGE_ENV" preview --root "$TEST_DIR" --dry-run
  [ "$status" -eq 0 ]
  [[ ! "$output" =~ "KEY_A" ]]
  [[ "$output" =~ "No missing keys" ]]
}

@test "merge_env.sh prod stage works too" {
  echo "KEY_A=alpha" > "$TEST_DIR/.env"
  echo "KEY_B=beta" > "$TEST_DIR/.env.prod"

  run bash "$MERGE_ENV" prod --root "$TEST_DIR" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ "+ KEY_A=alpha" ]]
}

@test "merge_env.sh fails when .env is missing" {
  echo "KEY_A=val" > "$TEST_DIR/.env.preview"

  run bash "$MERGE_ENV" preview --root "$TEST_DIR"
  [ "$status" -eq 1 ]
  [[ "$output" =~ ".env not found" ]]
}

@test "merge_env.sh fails when target file is missing" {
  echo "KEY_A=val" > "$TEST_DIR/.env"

  run bash "$MERGE_ENV" preview --root "$TEST_DIR"
  [ "$status" -eq 1 ]
  [[ "$output" =~ ".env.preview not found" ]]
}

# ── Syntax check ────────────────────────────────────────────────

@test "scripts/merge_env.sh syntax check" {
  run bash -n "$MERGE_ENV"
  [ "$status" -eq 0 ]
}
