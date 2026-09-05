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
}

@test "Makefile has knowledge-sync target" {
  run make -n knowledge-sync
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

