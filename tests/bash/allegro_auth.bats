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

# tests/bash/allegro_auth.bats
# Functional tests for scripts/allegro_auth.sh

bats_require_minimum_version 1.5.0

ALLEGRO_AUTH="./scripts/allegro_auth.sh"

# ── CLI interface tests ────────────────────────────────────────

@test "allegro_auth.sh --help exits 1 and prints usage" {
  run bash "$ALLEGRO_AUTH" --help
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "allegro_auth.sh -h exits 1 and prints usage" {
  run bash "$ALLEGRO_AUTH" -h
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Usage:" ]]
}

@test "allegro_auth.sh fails on unknown option" {
  run bash "$ALLEGRO_AUTH" --bogus-flag
  [ "$status" -eq 1 ]
  [[ "$output" =~ "Unknown option:" ]]
}

# ── Stack resolution tests (kill before API call) ──────────────

@test "allegro_auth.sh without --stack uses default .env" {
  run ! timeout 3 bash "$ALLEGRO_AUTH"
  [[ "$output" =~ "Env file:" ]]
  [[ "$output" =~ ".env" ]]
}

@test "allegro_auth.sh --stack preview targets preview config" {
  run ! timeout 3 bash "$ALLEGRO_AUTH" --stack preview
  [[ "$output" =~ "Stack:    preview" ]]
  [[ "$output" =~ ".env.preview" ]]
}

@test "allegro_auth.sh --stack prod targets prod config" {
  run ! timeout 3 bash "$ALLEGRO_AUTH" --stack prod
  [[ "$output" =~ "Stack:    prod" ]]
}

# ── Container restart after auth ────────────────────────────────

@test "allegro_auth.sh docker path includes restart after auth" {
  run grep -c 'restart web worker' "$ALLEGRO_AUTH"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
}
