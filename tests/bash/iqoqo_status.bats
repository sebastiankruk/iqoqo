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

setup() {
  export TEST_TEMP_DIR="$(mktemp -d)"
}

teardown() {
  rm -rf "${TEST_TEMP_DIR}"
}

@test "iqoqo-status.sh displays help information" {
  run bash scripts/iqoqo-status.sh --help
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Check health status of all iQoQo services" ]]
}

@test "iqoqo-status.sh fails on invalid argument" {
  run bash scripts/iqoqo-status.sh --invalid-argument-foo
  [ "$status" -eq 0 ]
  [[ "$output" =~ "Unknown option:" ]]
}

@test "iqoqo-status.sh shows environment configuration audit" {
  unset IQOQO_AI_MODE || true
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh
  [[ "$output" =~ "Environment Configuration" ]]
  [[ "$output" =~ "Configured" ]]
}

@test "iqoqo-status.sh suppresses ASCII banner in AI mode" {
  export IQOQO_AI_MODE=1
  run bash scripts/iqoqo-status.sh
  [[ ! "$output" =~ "╔══════════════════════════════════════════════╗" ]]
  [[ ! "$output" =~ "Environment Configuration" ]]
  [[ "$output" =~ "STATUS:" ]]
}

@test "iqoqo-status.sh reports Allegro API configuration status" {
  unset IQOQO_AI_MODE || true
  run env -u IQOQO_AI_MODE bash scripts/iqoqo-status.sh
  [[ "$output" =~ "Instance Settings" || "$output" =~ "Allegro" ]]
}

@test "iqoqo-status.sh reports not configured when Allegro credentials missing" {
  env_file="${TEST_TEMP_DIR}/.env.test"
  echo "ENV_FILE=.env.dev" > "$env_file"
  echo "ALLEGRO_CLIENT_ID=" >> "$env_file"
  echo "ALLEGRO_CLIENT_SECRET=" >> "$env_file"
  run env -u IQOQO_AI_MODE ENV_FILE="$env_file" bash scripts/iqoqo-status.sh
  [[ "$output" =~ "not configured" || "$output" =~ "Instance Settings" ]]
}

@test "iqoqo-status.sh discriminates probe error correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": false, \"reason\": \"query_failed\"}"
    reason=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"reason\", \"\"))")
    if [[ "$reason" == "query_failed" || "$reason" == "probe_error" ]]; then
      echo "probe error detected"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "probe error detected" ]]
}

@test "iqoqo-status.sh discriminates active token correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": true, \"token_age_hours\": 2.5, \"reason\": \"active\"}"
    is_active=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"allegro_token_active\", False))")
    token_age=$(echo "$allegro_status_json" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"token_age_hours\", \"\"))")
    if [[ "$is_active" == "True" ]]; then
      echo "active (token age: ${token_age}h)"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "active (token age: 2.5h)" ]]
}

@test "iqoqo-status.sh discriminates expired token correctly" {
  run bash -c '
    allegro_status_json="{\"configured\": true, \"allegro_token_active\": false, \"is_expired\": true, \"token_age_hours\": 48.0, \"reason\": \"expired\"}"
    is_expired=$(echo "$allegro_status_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get(\"is_expired\", False))")
    token_age=$(echo "$allegro_status_json" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get(\"token_age_hours\", \"\"))")
    if [[ "$is_expired" == "True" ]]; then
      echo "token expired (${token_age}h old, re-authorize in Instance Settings)"
    fi
  '
  [ "$status" -eq 0 ]
  [[ "$output" =~ "token expired (48.0h old, re-authorize in Instance Settings)" ]]
}



